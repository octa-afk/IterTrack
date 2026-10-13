import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from source.database.database import SessionLocal  # noqa: E402
from source.services.devices import provision_device  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision a GPS device and assign it to a truck.")
    parser.add_argument("--identifier", required=True, help="Hardware identifier, e.g. MAC address")
    parser.add_argument("--truck-id", required=True, type=int, help="Truck to assign the device to")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        token = provision_device(db, args.identifier, args.truck_id)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        db.close()

    print(f"Device token: {token}")
    print("WARNING: this token is shown only once. Store it on the device now.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
