import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse, parse_qs

def parse_major_requirements(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    requirements = {}
    all_tags = soup.find_all(["h2", "h3", "h4", "table"])

    current_req = None
    for tag in all_tags:
        if tag.name in ["h2", "h3", "h4"]:
            current_req = tag.get_text(strip=True)
            if current_req not in requirements:
                requirements[current_req] = []
        elif tag.name == "table" and current_req:
            for row in tag.find_all("tr")[1:]:  # Skip table header
                cells = row.find_all("td")
                if cells:
                    link = cells[0].find("a")
                    if link and "href" in link.attrs:
                        href = link["href"]
                        parsed_url = urlparse(href)
                        query = parse_qs(parsed_url.query)
                        course_code = unquote(query.get("P", [""])[0]).strip()
                        if course_code:
                            requirements[current_req].append(course_code)

    # Flatten: each course as its own key
    flat_courses = {course: [course] for section in requirements.values() for course in section}
    return flat_courses

if __name__ == "__main__":
    url = "https://guide.berkeley.edu/undergraduate/degree-programs/statistics/#majorrequirementstext"
    parsed = parse_major_requirements(url)
    with open("major_requirements.json", "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2)
    print(json.dumps(parsed, indent=2))
