import dns.resolver
from typing import List, Tuple


def get_mx_records(domain: str) -> List[Tuple[str, int]]:
    """
    Returns a list of MX records for the specified domain in the form of a
    list of tuples, where each tuple contains the mail server and its priority.
    """
    try:
        # Executes a request to receive MX records for the specified domain
        answers = dns.resolver.resolve(domain, 'MX')
        # Generates a list of tuples (mail server, priority) from the query results
        mx_records = [(str(r.exchange), r.preference) for r in answers]
        return sorted(mx_records, key=lambda record: record[1])
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return []


if __name__ == "__main__":
    # Specify your domain here to check MX records
    domain = "google.com"
    mx_records = get_mx_records(domain)
    if mx_records:
        print(f"MX records for the domain {domain}:")
        for record in mx_records:
            print(f"Server: {record[0]}, Priority: {record[1]}")
    else:
        print(f"MX records for the domain {domain} not found.")
