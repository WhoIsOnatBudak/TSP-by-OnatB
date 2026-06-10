import requests
from bs4 import BeautifulSoup


def print_secret(url):
    page = requests.get(url)
    page.raise_for_status()

    corba = BeautifulSoup(page.text, "html.parser")

    grid = {}

    max_x = 0
    max_y = 0

    table_rows = corba.find_all("tr")

    for row in table_rows:
        
        char = row.find_all("td")

        x_text = char[0].get_text().strip()

        if x_text == "x-coordinate":
            continue

        x_cord = int(x_text)

        max_x = max(max_x, x_cord)

        secret = char[1].get_text().strip()

        y_text = char[2].get_text().strip()

        y_cord = int(y_text)


        max_y = max(max_y, y_cord)

        grid[(x_cord, y_cord)] = secret
        

    for y in range(max_y, -1, -1):

        for x in range(max_x + 1):

            print(grid.get((x, y), " "), end="")

        print()

print_secret("https://docs.google.com/document/d/e/2PACX-1vSZ9d7OCd4QMsjJi2VFQmPYLebG2sGqI879_bSPugwOo_fgRcZLAFyfajPWU91UDiLg-RxRD41lVYRA/pub")
