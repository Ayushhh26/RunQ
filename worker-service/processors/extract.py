import spacy

_nlp = None


def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def preload_model():
    get_nlp()


def _unique_preserve_order(items):
    seen = set()
    out = []
    for item in items:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def extract_metadata(text: str) -> dict:
    nlp = get_nlp()
    doc = nlp(text)

    persons = []
    organizations = []
    dates = []
    amounts = []
    locations = []

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            persons.append(ent.text)
        elif ent.label_ == "ORG":
            organizations.append(ent.text)
        elif ent.label_ == "DATE":
            dates.append(ent.text)
        elif ent.label_ == "MONEY":
            amounts.append(ent.text)
        elif ent.label_ == "GPE":
            locations.append(ent.text)

    return {
        "persons": _unique_preserve_order(persons),
        "organizations": _unique_preserve_order(organizations),
        "dates": _unique_preserve_order(dates),
        "amounts": _unique_preserve_order(amounts),
        "locations": _unique_preserve_order(locations),
    }
