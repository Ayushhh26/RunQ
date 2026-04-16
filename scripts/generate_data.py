from pathlib import Path
import random

from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = BASE_DIR / "documents"

INVOICE_COUNT = 50
RESUME_COUNT = 50
REPORT_COUNT = 50


def clear_generated_documents():
    for path in DOCUMENTS_DIR.glob("invoice_*.txt"):
        path.unlink()
    for path in DOCUMENTS_DIR.glob("resume_*.txt"):
        path.unlink()
    for path in DOCUMENTS_DIR.glob("report_*.txt"):
        path.unlink()


def build_invoice_text():
    line_items = [
        "Systems integration services",
        "Cloud migration advisory",
        "Data pipeline implementation",
        "Quarterly maintenance support",
        "Infrastructure reliability audit",
        "Security compliance review",
    ]
    selected_items = random.sample(line_items, 3)
    amount = round(random.uniform(450.0, 12500.0), 2)
    issue_date = fake.date_between(start_date="-1y", end_date="today")
    due_date = fake.date_between(start_date=issue_date, end_date="+60d")
    return (
        f"Invoice Number: INV-{fake.random_number(digits=6, fix_len=True)}\n"
        f"Vendor: {fake.company()}\n"
        f"Client: {fake.company()}\n"
        f"Billing Address: {fake.address().replace(chr(10), ', ')}\n"
        f"Issue Date: {issue_date}\n"
        f"Due Date: {due_date}\n"
        f"Amount Due: ${amount:,.2f}\n\n"
        "Line Items:\n"
        f"- {selected_items[0]}\n"
        f"- {selected_items[1]}\n"
        f"- {selected_items[2]}\n\n"
        "Payment Terms: Net 30. Late payments incur a service charge.\n"
    )


def build_resume_text():
    skills_pool = [
        "Python",
        "FastAPI",
        "Redis",
        "PostgreSQL",
        "Docker",
        "Kubernetes",
        "CI/CD",
        "Prometheus",
        "Terraform",
        "Data Analysis",
        "Machine Learning",
        "System Design",
    ]
    skills = ", ".join(random.sample(skills_pool, 6))
    years_exp = random.randint(2, 12)
    return (
        f"Name: {fake.name()}\n"
        f"Location: {fake.city()}, {fake.country()}\n"
        f"Email: {fake.email()}\n"
        f"Phone: {fake.phone_number()}\n\n"
        "Professional Summary:\n"
        f"Engineer with {years_exp} years of experience building backend systems.\n\n"
        "Skills:\n"
        f"{skills}\n\n"
        "Education:\n"
        f"{fake.job()} Studies, {fake.company()} University\n\n"
        "Experience:\n"
        f"Led distributed processing initiatives at {fake.company()}.\n"
    )


def build_report_text():
    finding_templates = [
        "Queue latency increased during peak ingestion windows.",
        "Document validation reduced downstream failures by 22%.",
        "Worker utilization improved after horizontal scaling.",
        "Database checkpoints remained stable under sustained load.",
        "Retry traffic was concentrated in malformed file submissions.",
    ]
    recommendations = [
        "Introduce stricter file schema checks at submission time.",
        "Add queue depth alerts for proactive autoscaling.",
        "Capture per-job processing stages in metrics.",
        "Schedule periodic stale-job sweeps.",
        "Expand synthetic test corpus coverage by domain.",
    ]
    findings = random.sample(finding_templates, 3)
    recs = random.sample(recommendations, 3)
    return (
        f"Report Title: {fake.catch_phrase()}\n"
        f"Author: {fake.name()}\n"
        f"Created On: {fake.date_this_year()}\n\n"
        "Executive Summary:\n"
        "This report reviews operational behavior of the job processing system.\n\n"
        "Findings:\n"
        f"- {findings[0]}\n"
        f"- {findings[1]}\n"
        f"- {findings[2]}\n\n"
        "Recommendations:\n"
        f"- {recs[0]}\n"
        f"- {recs[1]}\n"
        f"- {recs[2]}\n"
    )


def write_documents(prefix, count, builder):
    for index in range(1, count + 1):
        path = DOCUMENTS_DIR / f"{prefix}_{index:03d}.txt"
        path.write_text(builder(), encoding="utf-8")


def main():
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    clear_generated_documents()
    write_documents("invoice", INVOICE_COUNT, build_invoice_text)
    write_documents("resume", RESUME_COUNT, build_resume_text)
    write_documents("report", REPORT_COUNT, build_report_text)
    print("Generated 150 documents: 50 invoices, 50 resumes, 50 reports.")


if __name__ == "__main__":
    main()
