"""Learn2Earn Campus Resource Management System.

Command-line program, Python standard library only.

Data model
----------
resources      list of dicts: id, name, category, total, available
fellows        dict: fellow ID -> fellow name
borrow_records list of dicts, one per successful borrowing (an audit log):
               fellow_id, resource_id, quantity (borrowed), returned (so far).
               Units currently on loan for a record = quantity - returned.
"""

import json
import os

DATA_FILE = "learn2earn_data.json"
LOW_STOCK_LIMIT = 3

resources = [
    {"id": "R001", "name": "Laptop", "category": "Electronics", "total": 10, "available": 10},
    {"id": "R002", "name": "Keyboard", "category": "Accessories", "total": 5, "available": 5},
    {"id": "R003", "name": "Headset", "category": "Accessories", "total": 3, "available": 3},
]

fellows = {"F001": "Ada", "F002": "John", "F003": "Grace"}

borrow_records = []


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def is_positive_int(value):
    """True only for real positive integers (bool is rejected)."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def on_loan(record):
    """Units of one borrowing record that have not been returned yet."""
    return record["quantity"] - record["returned"]


def find_resource(resource_id):
    """Return the resource dict for an ID (case/space-insensitive) or None."""
    wanted = str(resource_id).strip().upper()
    for resource in resources:
        if resource["id"].upper() == wanted:
            return resource
    return None


def find_fellow(fellow_id):
    """Return the fellow's name for an ID or None."""
    return fellows.get(str(fellow_id).strip().upper())


def units_on_loan(fellow_id, resource_id):
    """Units of a resource that one fellow currently has on loan."""
    return sum(
        on_loan(r)
        for r in borrow_records
        if r["fellow_id"] == fellow_id and r["resource_id"] == resource_id
    )


def validate_request(fellow_id, resource_id, quantity):
    """Check fellow, resource and quantity.

    Returns (fellow_name, resource) when valid. Otherwise prints a helpful
    error and returns None. Never changes any data.
    """
    fellow_name = find_fellow(fellow_id)
    if not fellow_name:
        print(f"Error: Fellow ID {str(fellow_id).strip()} not found.")
        return None

    resource = find_resource(resource_id)
    if not resource:
        print(f"Error: Resource ID {str(resource_id).strip()} not found.")
        return None

    if not is_positive_int(quantity):
        print("Error: Quantity must be a positive integer.")
        return None

    return fellow_name, resource


# --------------------------------------------------
# 1. RESOURCE INVENTORY
# --------------------------------------------------

def add_resource(resource_id, name, category, total):
    """Add a resource. Rejects blanks, duplicate IDs and bad totals."""
    resource_id = resource_id.strip().upper()
    name = name.strip()
    category = category.strip()

    if not resource_id or not name or not category:
        print("Error: ID, name and category are required.")
        return False

    if find_resource(resource_id):
        print(f"Error: Resource ID {resource_id} already exists.")
        return False

    if not is_positive_int(total):
        print("Error: Total units must be a positive integer.")
        return False

    resources.append({
        "id": resource_id,
        "name": name,
        "category": category,
        "total": total,
        "available": total,
    })
    print(f"Resource {resource_id} added successfully.")
    return True


def list_resources():
    """Print every resource."""
    print("\n--- RESOURCE INVENTORY ---")
    if not resources:
        print("No resources available.")
        return
    for r in resources:
        print(f'{r["id"]} | {r["name"]} | {r["category"]} | '
              f'Total: {r["total"]} | Available: {r["available"]}')


def update_resource(resource_id, new_name=None, new_category=None, new_total=None):
    """Change a resource's name, category or total units.

    Pass None for anything that should stay the same. The new total cannot be
    lower than the units currently on loan, and available units are adjusted
    so that available + on loan always equals total. All checks happen before
    any change, so a rejected update leaves the resource untouched.
    """
    resource = find_resource(resource_id)
    if not resource:
        print(f"Error: Resource ID {str(resource_id).strip()} not found.")
        return False

    if new_name is None and new_category is None and new_total is None:
        print("Nothing to update.")
        return False

    if new_name is not None and not new_name.strip():
        print("Error: Name cannot be blank.")
        return False
    if new_category is not None and not new_category.strip():
        print("Error: Category cannot be blank.")
        return False

    borrowed = resource["total"] - resource["available"]
    if new_total is not None:
        if not is_positive_int(new_total):
            print("Error: Total units must be a positive integer.")
            return False
        if new_total < borrowed:
            print(f'Error: {borrowed} unit(s) of {resource["name"]} are on loan, '
                  f"so the total cannot be below {borrowed}.")
            return False

    if new_name is not None:
        resource["name"] = new_name.strip()
    if new_category is not None:
        resource["category"] = new_category.strip()
    if new_total is not None:
        resource["total"] = new_total
        resource["available"] = new_total - borrowed

    print(f'Resource {resource["id"]} updated: {resource["name"]} | '
          f'{resource["category"]} | Total: {resource["total"]} | '
          f'Available: {resource["available"]}')
    return True


# --------------------------------------------------
# 2. BORROWING
# --------------------------------------------------

def borrow_item(fellow_id, resource_id, quantity):
    """Issue units to a fellow and log the borrowing.

    All checks happen before any change, so a rejected request leaves
    inventory and records untouched.
    """
    checked = validate_request(fellow_id, resource_id, quantity)
    if checked is None:
        return False
    fellow_name, resource = checked

    if quantity > resource["available"]:
        print(f'Error: Only {resource["available"]} unit(s) of '
              f'{resource["name"]} are available.')
        return False

    resource["available"] -= quantity
    borrow_records.append({
        "fellow_id": str(fellow_id).strip().upper(),
        "resource_id": resource["id"],
        "quantity": quantity,
        "returned": 0,
    })

    print(f'{fellow_name} borrowed {quantity} unit(s) of {resource["name"]}. '
          f'Available: {resource["available"]}')
    return True


# --------------------------------------------------
# 3. RETURNS
# --------------------------------------------------

def return_item(fellow_id, resource_id, quantity):
    """Accept a return, but only up to what the fellow has on loan."""
    checked = validate_request(fellow_id, resource_id, quantity)
    if checked is None:
        return False
    fellow_name, resource = checked

    fid = str(fellow_id).strip().upper()
    held = units_on_loan(fid, resource["id"])

    if quantity > held:
        print(f"Error: {fellow_name} currently has only {held} unit(s) of "
              f'{resource["name"]} on loan.')
        return False

    # Apply the return to this fellow's oldest open loans first.
    remaining = quantity
    for record in borrow_records:
        if remaining == 0:
            break
        if record["fellow_id"] == fid and record["resource_id"] == resource["id"]:
            amount = min(on_loan(record), remaining)
            record["returned"] += amount
            remaining -= amount

    resource["available"] += quantity

    print(f'{fellow_name} returned {quantity} unit(s) of {resource["name"]}. '
          f'Available: {resource["available"]}')
    return True


# --------------------------------------------------
# 4. SEARCH AND FILTER
# --------------------------------------------------

def search_by_name(name):
    """Case-insensitive partial name search."""
    text = name.strip().lower()
    print(f'\n--- SEARCH: "{name}" ---')

    if not text:
        print("Error: Enter a search term.")
        return

    matches = [r for r in resources if text in r["name"].lower()]
    if not matches:
        print("No matching resources found.")
        return
    for r in matches:
        print(f'{r["id"]} | {r["name"]} | {r["category"]} | Available: {r["available"]}')


def filter_by_category(category):
    """Case-insensitive category filter."""
    wanted = category.strip().lower()
    print(f'\n--- CATEGORY: "{category}" ---')

    matches = [r for r in resources if r["category"].lower() == wanted]
    if not matches:
        print("No resources found in this category.")
        return
    for r in matches:
        print(f'{r["id"]} | {r["name"]} | {r["category"]} | Available: {r["available"]}')


# --------------------------------------------------
# 5. REPORTS
# --------------------------------------------------

def get_borrowed_quantity(resource_id):
    """Units of a resource currently on loan across all fellows."""
    return sum(on_loan(r) for r in borrow_records if r["resource_id"] == resource_id)


def generate_report():
    """Print totals, low stock and the most borrowed resource(s)."""
    total_units = sum(r["total"] for r in resources)
    available_units = sum(r["available"] for r in resources)
    borrowed_units = sum(on_loan(r) for r in borrow_records)

    low_stock = [r for r in resources if r["available"] < LOW_STOCK_LIMIT]

    borrowed_counts = {r["id"]: get_borrowed_quantity(r["id"]) for r in resources}
    highest = max(borrowed_counts.values(), default=0)
    leaders = [r for r in resources
               if highest > 0 and borrowed_counts[r["id"]] == highest]

    print("\n--- INVENTORY REPORT ---")
    print(f"Total units: {total_units}")
    print(f"Available units: {available_units}")
    print(f"Units currently borrowed: {borrowed_units}")

    print(f"Resources with fewer than {LOW_STOCK_LIMIT} available units:")
    if low_stock:
        for r in low_stock:
            print(f'- {r["name"]} ({r["id"]}): {r["available"]} available')
    else:
        print("- None")

    print("Most borrowed resource(s) (units currently on loan):")
    if leaders:
        for r in leaders:
            print(f'- {r["name"]} ({r["id"]}): {borrowed_counts[r["id"]]} borrowed')
    else:
        print("- None")


# --------------------------------------------------
# BONUS: JSON PERSISTENCE
# --------------------------------------------------

def save_data(path=DATA_FILE):
    """Write inventory and loan records to a JSON file."""
    payload = {"resources": resources, "borrow_records": borrow_records}
    temp_path = path + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        os.replace(temp_path, path)  # never leaves a half-written file
    except OSError as error:
        print(f"Error: could not save data ({error}).")
        return False
    print(f"Data saved to {path}.")
    return True


def _is_valid_data(data):
    """Validate loaded JSON before it is allowed to replace live data."""
    try:
        loaded_resources = data["resources"]
        loaded_records = data["borrow_records"]

        ids = set()
        for r in loaded_resources:
            if not (isinstance(r["id"], str) and r["id"].strip()
                    and isinstance(r["name"], str) and r["name"].strip()
                    and isinstance(r["category"], str) and r["category"].strip()):
                return False
            if r["id"] in ids:
                return False
            ids.add(r["id"])
            if not is_positive_int(r["total"]):
                return False
            if (not isinstance(r["available"], int) or isinstance(r["available"], bool)
                    or not 0 <= r["available"] <= r["total"]):
                return False

        outstanding = {rid: 0 for rid in ids}
        for rec in loaded_records:
            if rec["fellow_id"] not in fellows or rec["resource_id"] not in ids:
                return False
            if not is_positive_int(rec["quantity"]):
                return False
            if (not isinstance(rec["returned"], int) or isinstance(rec["returned"], bool)
                    or not 0 <= rec["returned"] <= rec["quantity"]):
                return False
            outstanding[rec["resource_id"]] += rec["quantity"] - rec["returned"]

        # Stock and loans must agree: available + on loan == total.
        return all(r["available"] + outstanding[r["id"]] == r["total"]
                   for r in loaded_resources)
    except (KeyError, TypeError):
        return False


def load_data(path=DATA_FILE):
    """Replace live data with a saved file, only if the file is valid."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        print(f"Error: {path} does not exist yet. Save data first.")
        return False
    except (OSError, json.JSONDecodeError) as error:
        print(f"Error: could not read {path} ({error}).")
        return False

    if not _is_valid_data(data):
        print("Error: the file is not valid inventory data. Nothing was changed.")
        return False

    resources[:] = data["resources"]
    borrow_records[:] = data["borrow_records"]
    print(f"Data loaded from {path}.")
    return True


# --------------------------------------------------
# INPUT AND MENU
# --------------------------------------------------

def read_positive_integer(prompt):
    """Keep asking until the user enters a positive whole number."""
    while True:
        value = input(prompt).strip()
        try:
            number = int(value)
        except ValueError:
            print("Error: Enter a whole number, such as 1, 2 or 3.")
            continue
        if number <= 0:
            print("Error: Enter a positive integer.")
            continue
        return number


def add_resource_menu():
    resource_id = input("Resource ID: ")
    name = input("Resource name: ")
    category = input("Category: ")
    total = read_positive_integer("Total units: ")
    add_resource(resource_id, name, category, total)


def update_resource_menu():
    resource_id = input("Resource ID to update: ")
    if not find_resource(resource_id):
        print(f"Error: Resource ID {resource_id.strip()} not found.")
        return

    print("Press Enter to keep the current value.")
    name = input("New name: ").strip()
    category = input("New category: ").strip()
    total_text = input("New total units: ").strip()

    new_total = None
    if total_text:
        try:
            new_total = int(total_text)
        except ValueError:
            print("Error: Total units must be a whole number. Nothing was changed.")
            return

    update_resource(resource_id, name or None, category or None, new_total)


def borrow_menu():
    fellow_id = input("Fellow ID: ")
    resource_id = input("Resource ID: ")
    quantity = read_positive_integer("Quantity: ")
    borrow_item(fellow_id, resource_id, quantity)


def return_menu():
    fellow_id = input("Fellow ID: ")
    resource_id = input("Resource ID: ")
    quantity = read_positive_integer("Quantity: ")
    return_item(fellow_id, resource_id, quantity)


MENU_TEXT = """
======== LEARN2EARN RESOURCE SYSTEM ========
1. Add resource
2. List resources
3. Borrow resource
4. Return resource
5. Search by name
6. Filter by category
7. Generate report
8. Save data (JSON)
9. Load data (JSON)
10. Update resource
0. Exit
=============================================
"""


def menu():
    """Loop until the user chooses Exit (or input ends)."""
    actions = {
        "1": add_resource_menu,
        "2": list_resources,
        "3": borrow_menu,
        "4": return_menu,
        "5": lambda: search_by_name(input("Enter resource name: ")),
        "6": lambda: filter_by_category(input("Enter category: ")),
        "7": generate_report,
        "8": save_data,
        "9": load_data,
        "10": update_resource_menu,
    }

    while True:
        print(MENU_TEXT)
        try:
            choice = input("Choose an option: ").strip()
            if choice == "0":
                print("Goodbye.")
                break
            action = actions.get(choice)
            if action:
                action()
            else:
                print("Error: Please choose an option from 0 to 10.")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break


# --------------------------------------------------
# REQUIRED DEMONSTRATION
# --------------------------------------------------

def stock_of(resource_id):
    return find_resource(resource_id)["available"]


def report_stock(label, resource_id, before):
    """Compare stock with a snapshot and print the true result."""
    after = stock_of(resource_id)
    if before == after:
        print(f"{label} stock unchanged: {before} -> {after}")
    else:
        print(f"WARNING: {label} stock changed: {before} -> {after}")


def run_required_demonstration():
    """Run steps 1-7 in order, plus one extra invalid-input test."""
    print("========== REQUIRED DEMONSTRATION ==========")

    print("\n1. F001 borrows 2 laptops")
    borrow_item("F001", "R001", 2)

    print("\n2. F002 borrows 3 keyboards")
    borrow_item("F002", "R002", 3)

    print("\n3. F001 returns 1 laptop")
    return_item("F001", "R001", 1)

    print("\n4. F003 requests 4 headsets")
    before = stock_of("R003")
    borrow_item("F003", "R003", 4)
    report_stock("Headset", "R003", before)

    print("\n5. F002 tries to return 4 keyboards")
    before = stock_of("R002")
    return_item("F002", "R002", 4)
    report_stock("Keyboard", "R002", before)

    print("\n6. Search for LAPtop")
    search_by_name("LAPtop")

    print("\n7. Generate the report")
    generate_report()

    print("\nAdditional invalid-input test: F001 borrows 0 laptops")
    before = stock_of("R001")
    borrow_item("F001", "R001", 0)
    report_stock("Laptop", "R001", before)


if __name__ == "__main__":
    run_required_demonstration()
    menu()
