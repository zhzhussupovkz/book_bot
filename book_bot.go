package main

import (
    "fmt"
    "net/http"
    "io/ioutil"
    "os"
)

const main_url string = "http://www.e-reading.club"
const book_author_xpath string = ".//table//a[contains(@href, 'bookbyauthor')]/@href"

func main() {
    response, err := http.Get(main_url)
    if err != nil {
        fmt.Printf("%s", err)
        os.Exit(1)
    } else {
        defer response.Body.Close()
        contents, err := ioutil.ReadAll(response.Body)
        if err != nil {
            fmt.Printf("%s", err)
            os.Exit(1)
        }

    }
}
