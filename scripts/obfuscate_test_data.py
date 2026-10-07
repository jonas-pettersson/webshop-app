"""
Script to obfuscate personal data in test files for safe public repository storage.

This script replaces:
- Real names with fake Swedish/Austrian names
- Real emails with fake emails
- Real phone numbers with fake phone numbers
- Preserves data structure and relationships
"""

import pandas as pd
import random
from pathlib import Path

# Fake names (Swedish/Austrian style)
FIRST_NAMES = [
    'Anna', 'Erik', 'Maria', 'Lars', 'Karin', 'Johan', 'Sofia', 'Peter',
    'Emma', 'Anders', 'Lisa', 'Karl', 'Ingrid', 'Gustav', 'Helena', 'Magnus',
    'Kristina', 'Sven', 'Eva', 'Nils', 'Birgitta', 'Hans', 'Margareta', 'Olof'
]

LAST_NAMES = [
    'Andersson', 'Johansson', 'Karlsson', 'Nilsson', 'Eriksson', 'Larsson',
    'Olsson', 'Persson', 'Svensson', 'Gustafsson', 'Pettersson', 'Jonsson',
    'Jansson', 'Hansson', 'Bengtsson', 'Schmidt', 'Müller', 'Weber', 'Fischer'
]

def generate_fake_name():
    """Generate a fake Swedish/Austrian name."""
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def generate_fake_email(index):
    """Generate a fake but consistent email address."""
    domains = ['example.com', 'test.se', 'demo.at', 'sample.com']
    return f"test.user{index}@{random.choice(domains)}"

def generate_fake_phone():
    """Generate a fake Austrian/Swedish phone number."""
    prefixes = ['0660', '0664', '0676', '0699', '070', '073']
    return f"{random.choice(prefixes)}-{random.randint(1000000, 9999999)}"

def obfuscate_orders(input_path, output_path):
    """Obfuscate orders.xlsx file."""
    print(f"Obfuscating {input_path}...")

    df = pd.read_excel(input_path)

    # Create consistent mapping for emails (to preserve relationships)
    unique_emails = df['Email (Billing)'].dropna().unique()
    email_mapping = {email: generate_fake_email(i) for i, email in enumerate(unique_emails)}

    # Create consistent mapping for names
    unique_names = df['Full Name (Billing)'].dropna().unique()
    name_mapping = {name: generate_fake_name() for name in unique_names}

    # Create consistent mapping for phone numbers
    unique_phones = df['Phone (Billing)'].dropna().unique()
    phone_mapping = {phone: generate_fake_phone() for phone in unique_phones}

    # Apply mappings
    df['Email (Billing)'] = df['Email (Billing)'].map(email_mapping)
    df['Full Name (Billing)'] = df['Full Name (Billing)'].map(name_mapping)
    df['Phone (Billing)'] = df['Phone (Billing)'].map(phone_mapping)

    # Obfuscate customer notes if they contain personal info
    if 'Customer Note' in df.columns:
        df['Customer Note'] = df['Customer Note'].fillna('').apply(
            lambda x: 'Test order note' if x and len(str(x)) > 0 else ''
        )

    df.to_excel(output_path, index=False)
    print(f"  -> Saved to {output_path}")

    return email_mapping, name_mapping, phone_mapping

def obfuscate_timeslots(input_path, output_path, email_mapping, name_mapping, phone_mapping):
    """Obfuscate tidsbokning.csv file using consistent mappings from orders."""
    print(f"Obfuscating {input_path}...")

    df = pd.read_csv(input_path, encoding='latin_1')

    # Apply email mapping (use existing mapping to preserve relationships)
    df['Email'] = df['Email'].map(lambda x: email_mapping.get(x, generate_fake_email(random.randint(1000, 9999))))

    # Apply name mapping or generate new names
    df['Name'] = df['Name'].map(lambda x: name_mapping.get(x, generate_fake_name()))

    # Obfuscate phone numbers
    df['Telefon'] = df['Telefon'].apply(
        lambda x: phone_mapping.get(x, generate_fake_phone()) if pd.notna(x) and str(x).strip() else x
    )

    df.to_csv(output_path, index=False, encoding='latin_1')
    print(f"  -> Saved to {output_path}")

def main():
    """Main obfuscation process."""
    fixture_dir = Path(__file__).parent.parent / 'tests' / 'fixtures' / 'pask'

    print("=" * 60)
    print("Obfuscating test data to remove personal information")
    print("=" * 60)

    # Obfuscate orders (creates mappings)
    orders_input = fixture_dir / 'orders.xlsx'
    orders_output = fixture_dir / 'orders_obfuscated.xlsx'
    email_map, name_map, phone_map = obfuscate_orders(orders_input, orders_output)

    # Obfuscate timeslots (uses mappings to preserve relationships)
    timeslots_input = fixture_dir / 'tidsbokning.csv'
    timeslots_output = fixture_dir / 'tidsbokning_obfuscated.csv'
    obfuscate_timeslots(timeslots_input, timeslots_output, email_map, name_map, phone_map)

    print("\n" + "=" * 60)
    print("Obfuscation complete!")
    print("=" * 60)
    print(f"\nNext steps:")
    print(f"1. Review obfuscated files:")
    print(f"   - {orders_output}")
    print(f"   - {timeslots_output}")
    print(f"2. If satisfied, replace original files:")
    print(f"   mv {orders_output} {orders_input}")
    print(f"   mv {timeslots_output} {timeslots_input}")
    print(f"3. Remove from git history and re-commit")

if __name__ == '__main__':
    main()
