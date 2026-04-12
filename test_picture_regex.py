"""Quick regex test for picture tag parsing."""
import re

PICTURE_RE = re.compile(r"\s*\[PICTURE:\s*(chester|pat)\s*\]\s*$", re.IGNORECASE)

test_cases = [
    ("Great question! Chester just turned 3 last month 🐶\n[PICTURE: chester]", "chester", "Chester pic with text"),
    ("Oh you want to see me? Sure thing!\n[PICTURE: pat]", "pat", "Pat pic with text"),
    ("Chester is such a good boy, I love him so much!", None, "No picture mentioned"),
    ("  [PICTURE: Chester]  ", "chester", "Only picture tag, whitespace"),
    ("Here is a picture of my dog:\n[PICTURE: chester]", "chester", "Intro text then pic tag"),
    ("Can you send me a picture of Chester please?\n[PICTURE: chester]", "chester", "Explicit request for Chester"),
    ("No picture for you", None, "Negative case"),
    ("[PICTURE: PAT]", "pat", "Uppercase PAT"),
]

print("Testing PICTURE_RE...")
all_passed = True
for text, expected_subject, description in test_cases:
    match = PICTURE_RE.search(text)
    if expected_subject is None:
        if match:
            print(f"FAIL: {description} — expected None but got {match.group(1)}")
            all_passed = False
        else:
            print(f"PASS: {description}")
    else:
        if not match:
            print(f"FAIL: {description} — expected {expected_subject} but got None")
            all_passed = False
        else:
            subject = match.group(1).lower()
            clean = PICTURE_RE.sub("", text).strip()
            if subject != expected_subject:
                print(f"FAIL: {description} — subject={subject}, expected={expected_subject}")
                all_passed = False
            else:
                print(f"PASS: {description} | subject={subject} | clean={repr(clean)}")

print()
print("All tests passed!" if all_passed else "SOME TESTS FAILED")
