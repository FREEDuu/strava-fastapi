import csv
import io
import schemas
from typing import List

def generate_csv(activities: List[schemas.Activity]):
    """Generates CSV content from a list of Activity objects."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    if activities:
        header = [field for field in activities[0].__dict__ if not field.startswith('_')]
        writer.writerow(header)

    # Write data rows
    for activity in activities:
        row = [getattr(activity, field) for field in header]
        writer.writerow(row)

    return output.getvalue()