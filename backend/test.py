from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSeXQDdn14TD0UtYsL8Urbom8uoTkfuAE52IsIZUfqDQw6ypyA/viewform?usp=header"

options = Options()
# options.add_argument("--headless=new")

driver = webdriver.Chrome(options=options)

try:
    driver.get(FORM_URL)

    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located(
            (By.TAG_NAME, "body")
        )
    )

    time.sleep(5)

    print("\n" + "=" * 80)
    print("PAGE TITLE")
    print("=" * 80)
    print(driver.title)

    print("\n" + "=" * 80)
    print("ROLE SUMMARY")
    print("=" * 80)

    roles = {}

    for el in driver.find_elements(By.CSS_SELECTOR, "[role]"):
        role = el.get_attribute("role")
        roles[role] = roles.get(role, 0) + 1

    for role, count in sorted(roles.items()):
        print(f"{role}: {count}")

    print("\n" + "=" * 80)
    print("LISTITEMS")
    print("=" * 80)

    listitems = driver.find_elements(
        By.CSS_SELECTOR,
        "div[role='listitem']"
    )

    print("Found:", len(listitems))

    for idx, item in enumerate(listitems):

        print("\n")
        print("=" * 80)
        print(f"QUESTION BLOCK {idx+1}")
        print("=" * 80)

        try:
            print(item.text)
        except:
            pass

        radios = item.find_elements(
            By.CSS_SELECTOR,
            "[role='radio']"
        )

        if radios:
            print("\nRADIO OPTIONS:")
            for r in radios:
                print({
                    "aria-label": r.get_attribute("aria-label"),
                    "text": r.text,
                    "class": r.get_attribute("class")
                })

        checkboxes = item.find_elements(
            By.CSS_SELECTOR,
            "[role='checkbox']"
        )

        if checkboxes:
            print("\nCHECKBOX OPTIONS:")
            for c in checkboxes:
                print({
                    "aria-label": c.get_attribute("aria-label"),
                    "text": c.text,
                    "class": c.get_attribute("class")
                })

        textboxes = item.find_elements(
            By.CSS_SELECTOR,
            "input, textarea"
        )

        if textboxes:
            print("\nTEXT INPUTS:")
            for t in textboxes:
                print({
                    "tag": t.tag_name,
                    "type": t.get_attribute("type"),
                    "name": t.get_attribute("name"),
                    "placeholder": t.get_attribute("placeholder"),
                    "aria-label": t.get_attribute("aria-label")
                })

    print("\n" + "=" * 80)
    print("FULL DOM SNAPSHOT")
    print("=" * 80)

    elements = driver.find_elements(
        By.CSS_SELECTOR,
        "[role='radio'],[role='checkbox'],input,textarea,select"
    )

    dump = []

    for el in elements:

        dump.append({
            "tag": el.tag_name,
            "role": el.get_attribute("role"),
            "type": el.get_attribute("type"),
            "name": el.get_attribute("name"),
            "aria_label": el.get_attribute("aria-label"),
            "text": el.text,
            "class": el.get_attribute("class")
        })

    with open("google_form_dump.json", "w", encoding="utf-8") as f:
        json.dump(
            dump,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"\nSaved {len(dump)} elements to google_form_dump.json")

finally:
    input("\nPress Enter to close browser...")
    driver.quit()