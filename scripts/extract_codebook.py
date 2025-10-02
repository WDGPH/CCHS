# Improved extraction for categories and harmonization structure
import PyPDF2
import re
import json

def extract_variables_with_categories(pdf_path):
    variables = {}
    current_variable = None
    current_description = None
    codes = {}
    in_answer_categories = False

    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text = page.extract_text()
            lines = text.splitlines()
            for line in lines:
                if "Variable Name:" in line:
                    if current_variable:
                        variables[current_variable] = {
                            "description": current_description,
                            "categories": codes.copy() if codes else {}
                        }
                    current_variable = line.split(":")[1].strip().replace(" Length", "")
                    current_description = None
                    codes = {}
                    in_answer_categories = False
                elif "Concept:" in line:
                    current_description = line.split(":")[1].strip()
                elif "Answer Categories" in line:
                    in_answer_categories = True
                    continue
                elif in_answer_categories:
                    # Debug print to see what lines are being processed
                    print(f"Category line: {line}")
                    # Try to match: label (text) code (1-3 digits) freq freq %
                    match = re.match(r"^(.+?)\s+(\d{1,3})\s+\d[\d,]*\s+\d[\d,]*\s+[\d.]+", line)
                    if match:
                        meaning = match.group(1).strip()
                        code = match.group(2).strip()
                        codes[code] = meaning
                    # End of categories section
                    elif line.strip() == "" or re.match(r"^(Note:|Source:|Universe:|Total)", line):
                        in_answer_categories = False
                        continue
                elif "Note:" in line or "Source:" in line or "Universe:" in line:
                    in_answer_categories = False
                    continue
    if current_variable:
        variables[current_variable] = {
            "description": current_description,
            "categories": codes.copy() if codes else {}
        }
    return variables

# Example usage:
pdf_path = "./codebooks/CCHS_2023_DataDictionary_Freqs_ON.pdf"  # Input from codebooks folder
variables = extract_variables_with_categories(pdf_path)

# Save as JSON for harmonization pipeline
test_json_path = "./harmonization/CCHS_2023.json"  # Output to harmonization folder
with open(test_json_path, "w", encoding="utf-8") as f:
    json.dump(variables, f, indent=2, ensure_ascii=False)

print(f"Extracted variable/category info saved to {test_json_path}")
