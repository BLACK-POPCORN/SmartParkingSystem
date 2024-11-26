import os

def get_parking_lot_ids_from_csv():
    """
    Retrieve all parking lot IDs from the 'Data/ParkingAvailability' directory.

    Returns:
    - parking_lot_ids (set): A set of parking lot IDs obtained from CSV files.
    """
    # Get all parking lot IDs from 'Data/ParkingAvailability' folder
    parking_lot_ids = []
    for filename in os.listdir('Data/ParkingAvailability'):
        if filename.endswith('.csv'):
            parking_lot_id = filename[:-4]  # Remove the '.csv' extension
            parking_lot_ids.append(parking_lot_id)
    return set(parking_lot_ids)

def get_parking_lot_ids_from_deploy():
    """
    Retrieve all parking lot IDs from the 'deploy_lstm' directory.

    Returns:
    - parking_lot_ids (set): A set of parking lot IDs obtained from the deployment folders.
    """
    # Get all parking lot IDs from 'deploy_lstm' folder
    parking_lot_ids = []
    for name in os.listdir('deploy_lstm'):
        path = os.path.join('deploy_lstm', name)
        if os.path.isdir(path):
            parking_lot_ids.append(name)
    return set(parking_lot_ids)

def main():
    """
    Main function to find and display parking lot IDs for which models were not successfully generated.
    """
    csv_parking_lots = get_parking_lot_ids_from_csv()
    deploy_parking_lots = get_parking_lot_ids_from_deploy()
    missing_parking_lots = csv_parking_lots - deploy_parking_lots
    print("Parking lot IDs for which models were not successfully generated:")
    for parking_lot in sorted(missing_parking_lots):
        print(parking_lot)

if __name__ == '__main__':
    main()