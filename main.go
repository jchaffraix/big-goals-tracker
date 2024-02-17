package main

import (
  "context"
  //"crypto/rand"
  "crypto/sha256"
  //"encoding/json"
  "fmt"
  //"io"
  "log"
  "net/http"
  "os"
  "strings"

  "github.com/julienschmidt/httprouter"

  "cloud.google.com/go/datastore"
  "google.golang.org/appengine/v2"
  "google.golang.org/appengine/v2/user"
)

const (
  kCountsKind = "Counts"
  kEmailHashKind = "UserEmailHash"
  kEmailKind = "UserEmail"
)

func getSaltForUser(dsClient *datastore.Client, u *user.User) string {
  var ancestorKey = datastore.NameKey(kEmailKind, u.ID, nil)

  var existingSalt []string
  q := datastore.NewQuery(kEmailKind).Ancestor(ancestorKey).Limit(10)
  if _, err := dsClient.GetAll(context.Background(), q, &existingSalt); err != nil {
    panic(fmt.Sprintf("Error getting the \"%s\" from datastore: %+v", kEmailKind, err))
  }

  if len(existingSalt) > 1 {
    panic(fmt.Sprintf("Several salts are stored for user %s, data corruption is about to happen", u.Email))
  } else if len(existingSalt) == 0 {
    panic("Disabling new user login until datastore migration is resolved")
    /*var new_salt [64]byte
    read, err := rand.Read(new_salt)
    if err != nil || read != 64 {
      panic(fmt.Sprintf("Error reading random bytes (read=%d, err=%+v)", read, err)
    }

    if _, err := dsClient.Put(context.Background(), k, &e); err != nil {
      panic(fmt.Sprintf("Error storing salt for new user %s, err=%+v", u.Email, err)
    }
    return new_salt*/
  } else {
    return existingSalt[0]
  }
}

func ancestorKey(dsClient *datastore.Client, u *user.User) *datastore.Key {
  salt := getSaltForUser(dsClient, u)
  salted_id_raw := sha256.Sum256([]byte(salt + u.ID))
  salted_id := string(salted_id_raw[:])
  return datastore.NameKey(kEmailHashKind, salted_id, nil)
}

func isUserAllowed(u *user.User) bool {
  if u.Admin {
    return true
  }

  email := strings.ToLower(u.Email)
  email_hash_raw := sha256.Sum256([]byte(email))
  email_hash := string(email_hash_raw[:])
  if email_hash == "be101762cccb1ff52ca83fdbe45aeb59a919e7088f3fcbdb2d83729a4e65b143" {
    return true
  }

  fmt.Printf("Rejected email %s (hash %s)\n", email, email_hash)
  return false
}

// TODO: I should ouput some kind of apache-style log.
func logRequest(req *http.Request) {
  log.Printf("Received request for %s", req.URL.String())
}

func renderFailedPage(w http.ResponseWriter) {
  w.Header().Add("Content-Type", "text/html")
  w.WriteHeader(http.StatusInternalServerError)
  w.Write([]byte(`<!DOCTYPE html>
<meta charset="UTF-8">
<p>Something failed on our end!</p>`))
}

func mainPageHandler(w http.ResponseWriter, req *http.Request, ps httprouter.Params) {
  logRequest(req)

  if req.URL.Path != "/" {
    http.NotFound(w, req)
    return
  }

  ctx := appengine.NewContext(req)
  u := user.Current(ctx)
  if u == nil {
    url, err := user.LoginURL(ctx, "/")
    if err != nil {
      log.Printf("Error generating rediction URL (%+v)", err)
      renderFailedPage(w)
      return
    }
    log.Printf("Unsigned user, redirecting to %s", url)
    http.Redirect(w, req, url, http.StatusFound)
    return
  }

  if !isUserAllowed(u) {
    w.WriteHeader(http.StatusForbidden)
    // TODO: Put some content-type + content.
    return
  }

  main_page, err := os.ReadFile("index.html")
  if err != nil {
    log.Printf("Error reading homepage %+v", err)
    renderFailedPage(w)
    return

  }
  w.Header().Add("Content-Type", "text/html")
  w.Write([]byte(main_page))
}

type Counts struct {
  updatedDate string
  physicalCount []int `json:"physicalCount"`
  wellBeingCount []int `json:"wellBeingCount"`
  moneyCount []int `json:"moneyCount"`
  relationshipsCount []int `json:"relationshipsCount"`
  // Whether the counts where submitted.
  // There should be only one unsubmitted Counts at all time per user.
  // TODO: We should really split this out of our datamodel.
  submitted bool `json:"submitted"`
}

func (c *Counts) toJSONSummary() string {
  return fmt.Sprintf(`{"updatedDate":"%s", "physicalCount":%d, "wellBeingCount":%d, "moneyCount":%d, "relationshipsCount":%d}`, c.updatedDate, len(c.physicalCount), len(c.wellBeingCount), len(c.moneyCount), len(c.relationshipsCount))
}

func saveHandler(w http.ResponseWriter, req *http.Request, ps httprouter.Params) {
  logRequest(req)

  // TODO: handle query param: submit.
  ctx := context.Background()
  u := user.Current(ctx)
  if u == nil {
    url, err := user.LoginURL(ctx, "/")
    if err != nil {
      log.Printf("Error generating rediction URL (%+v)", err)
      renderFailedPage(w)
      return
    }
    log.Printf("Unsigned user, redirecting to %s", url)
    http.Redirect(w, req, url, http.StatusFound)
    return
  }

  if !isUserAllowed(u) {
    w.WriteHeader(http.StatusForbidden)
    // TODO: Put some content-type + content.
    return
  }

  // TODO: Disabling any write API while I iron out the queries.
  renderFailedPage(w)
  return

  /*body, err := io.ReadAll(req.Body)
  if err != nil {
    log.Printf("Error reading req body: %+v", err)
    renderFailedPage(w)
    return
  }
  defer req.Body.Close()

  var newCounts Counts
  err = json.Unmarshal(body, &newCounts)
  if err != nil {
    log.Printf("Error unmarshaling req body: %+v", err)
    renderFailedPage(w)
    return
  }
  dsClient, err := datastore.NewClient(ctx, "")
  if err != nil {
    log.Printf("Error creating datastore client: %+v", err)
    renderFailedPage(w)
    return
  }
  defer dsClient.Close()

  var unsubmittedCounts []Counts
  q := datastore.NewQuery(kCountsKind).Filter("submitted =", false).Order("-updateDate").Limit(10)
  if _, err := dsClient.GetAll(ctx, q, &unsubmittedCounts); err != nil {
    log.Printf("Error getting the \"%s\" from datastore: %+v", kCountsKind, err)
    renderFailedPage(w)
    return
  }

  unsubmittedCountsLen := len(unsubmittedCounts)
  if unsubmittedCountsLen == 0 {
    k := datastore.NameKey("UserEmailHash", "stringID", nil)
    if _, err := dsClient.Put(ctx, k, &newCount); err != nil {
      log.Printf("Error storing \"%s\" into datastore: %+v", kCountsKind, err)
      renderFailedPage(w)
      return
    }
    w.Write("Saved")
  } else if unsubmittedCountsLen == 1 {
    // TODO: Handle.
  } else {
    // TODO: panic?
  }*/
}

func getOldHandler(w http.ResponseWriter, req *http.Request, ps httprouter.Params) {
  logRequest(req)

  // TODO: handle query param: submit.
  ctx := context.Background()
  u := user.Current(ctx)
  if u == nil {
    url, err := user.LoginURL(ctx, "/")
    if err != nil {
      log.Printf("Error generating rediction URL (%+v)", err)
      renderFailedPage(w)
      return
    }
    log.Printf("Unsigned user, redirecting to %s", url)
    http.Redirect(w, req, url, http.StatusFound)
    return
  }

  if !isUserAllowed(u) {
    w.WriteHeader(http.StatusForbidden)
    // TODO: Put some content-type + content.
    return
  }
  log.Printf("Requesting info for user: %s", u.Email)

  dsClient, err := datastore.NewClient(ctx, "")
  if err != nil {
    log.Printf("Error creating datastore client: %+v", err)
    renderFailedPage(w)
    return
  }
  defer dsClient.Close()

  var latestSubmittedEntries []Counts
  q := datastore.NewQuery(kCountsKind).Ancestor(ancestorKey(dsClient, u)).Filter("submitted =", true).Order("-updateDate").Limit(10)
  if _, err := dsClient.GetAll(ctx, q, &latestSubmittedEntries); err != nil {
    log.Printf("Error getting the \"%s\" from datastore: %+v", kCountsKind, err)
    renderFailedPage(w)
    return
  }

  if len(latestSubmittedEntries) == 0 {
    log.Printf("No submitted entries for user %s", u.Email)
  }

  json := `{"logs":[`
  for i, entry := range latestSubmittedEntries {
    json += entry.toJSONSummary()
    if i != len(latestSubmittedEntries) - 1 {
      json += ","
    }
  }
  json += `]}`
  w.Header().Add("Content-Type", "application/json")
  w.Write([]byte(json))
}


func main() {
  router := httprouter.New()
  router.GET("/", mainPageHandler)
  // TODO: Rewrite the route to follow REST.
  router.POST("/save", saveHandler)
  router.GET("/getOld", getOldHandler)
  // Note: Some limitations of ServeFile are:
  // 1. that if there is no 'index.html' in the directory, this will show the directory.
  // 2. there is no Content-Type set on the file served.
  router.ServeFiles("/semantic/*filepath", http.Dir("semantic"))

  port := os.Getenv("PORT")
  if port == "" {
    port = "8080"
  }


  log.Printf("Listening on port=%s", port)
  if err := http.ListenAndServe(":" + port, router); err != nil {
    log.Fatal(err)
  }
  log.Printf("Closing...")
}
