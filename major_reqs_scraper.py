import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse, parse_qs

def parse_cs_requirements_from_web(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    valid_sections = [
        "Lower Division Requirement",
        "Upper Division Requirements",
        "Approved Non-Computer Science Technical Electives"
    ]

    requirements = {}
    all_tags = soup.find_all(["h2", "h3", "h4", "table"])

    current_req = None
    stop_after = "Approved Non-Computer Science Technical Electives"
    for tag in all_tags:
        if tag.name in ["h2", "h3", "h4"]:
            heading = tag.get_text(strip=True)
            if heading == stop_after and heading not in requirements:
                current_req = heading
                requirements[current_req] = []
            elif heading in valid_sections:
                current_req = heading
                requirements[current_req] = []
            elif heading not in valid_sections and current_req == stop_after:
                break  # Stop processing after the last valid section
        elif tag.name == "table" and current_req:
            for row in tag.find_all("tr")[1:]:
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

    # Flatten the nested dict into a single-course format
    flat_courses = {course: [course] for courses in requirements.values() for course in courses}

    return flat_courses

if __name__ == "__main__":
    url = "https://guide.berkeley.edu/undergraduate/degree-programs/computer-science/#majorrequirementstext"
    parsed = parse_cs_requirements_from_web(url)
    with open("cs_requirements.json", "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2)
    print(json.dumps(parsed, indent=2))
