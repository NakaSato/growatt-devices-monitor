#!/usr/bin/env python3
"""
Plants Data Collector Tests

This module contains tests for the PlantsDataCollector class.
These tests use real connections to databases and APIs (no mocking).
"""

import os
import sys
import unittest
from datetime import datetime
import psycopg2
import json

# Add the parent directory to the path so we can import from the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from script.plants_data_collector import PlantsDataCollector
from app.config import Config


class TestPlantsDataCollector(unittest.TestCase):
    """Tests for the PlantsDataCollector class"""

    def setUp(self):
        """Set up the test by creating a collector instance and test data"""
        self.collector = PlantsDataCollector()
        
        # Create a connection to the database to clean up before and after tests
        self.conn = self.collector.connect_to_db()
        self.cursor = self.conn.cursor()
    
    def tearDown(self):
        """Clean up after the test"""
        # Close the database connection
        if self.conn:
            self.conn.close()
    
    def test_database_connection(self):
        """Test that we can connect to the database"""
        conn = self.collector.connect_to_db()
        self.assertIsNotNone(conn)
        conn.close()
    
    def test_authentication(self):
        """Test authentication with the Growatt API"""
        # This test will actually try to authenticate with real credentials
        result = self.collector.authenticate()
        self.assertTrue(result)
        self.assertTrue(self.collector.is_authenticated)
    
    def test_fetch_plants(self):
        """Test fetching plants from the API"""
        # First authenticate
        self.collector.authenticate()
        
        # Then fetch plants
        plants = self.collector.fetch_plants()
        self.assertIsNotNone(plants)
        self.assertIsInstance(plants, list)
        
        if len(plants) > 0:
            # Check that the first plant has the expected fields
            first_plant = plants[0]
            self.assertIn('id', first_plant)
            # Print the first plant for debugging
            print(f"Sample plant data: {json.dumps(first_plant, indent=2)}")

    def test_modified_save_plants_to_db(self):
        """Test saving plants to the database with a simplified schema"""
        # First authenticate and fetch plants
        self.collector.authenticate()
        plants = self.collector.fetch_plants()
        
        if not plants or len(plants) == 0:
            self.skipTest("No plants found, skipping database save test")
        
        # Save using a simplified schema that matches your actual database
        conn = None
        try:
            conn = self.collector.connect_to_db()
            cursor = conn.cursor()
            
            timestamp = datetime.now()
            saved_count = 0
            
            for plant in plants:
                try:
                    # Get the plant ID and name
                    plant_id = plant.get('id', '')
                    plant_name = plant.get('name', '') or plant.get('plantName', '')
                    
                    # Convert status codes to text if needed
                    status = plant.get('status', 'unknown')
                    if status == '1':
                        status = 'active'
                    elif status == '2':
                        status = 'warning'
                    elif status == '3':
                        status = 'error'
                    elif status == '0':
                        status = 'offline'
                    
                    # Insert with just the fields that actually exist in your table
                    cursor.execute(
                        """
                        INSERT INTO plants (id, name, status, last_updated)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            status = EXCLUDED.status,
                            last_updated = EXCLUDED.last_updated
                        """,
                        (
                            plant_id,
                            plant_name,
                            status,
                            timestamp
                        )
                    )
                    saved_count += 1
                except Exception as e:
                    print(f"Error saving plant {plant_id}: {e}")
            
            conn.commit()
            print(f"Successfully saved {saved_count} plants")
            
            # Verify the plants were saved
            cursor.execute("SELECT COUNT(*) FROM plants")
            count = cursor.fetchone()[0]
            self.assertGreater(count, 0)
            
            # Verify the first plant was saved correctly with detailed field comparison
            first_plant = plants[0]
            plant_id = first_plant.get('id', '')
            plant_name = first_plant.get('name', '') or first_plant.get('plantName', '')
            
            # Convert status code to text for comparison
            expected_status = first_plant.get('status', 'unknown')
            if expected_status == '1':
                expected_status = 'active'
            elif expected_status == '2':
                expected_status = 'warning'
            elif expected_status == '3':
                expected_status = 'error'
            elif expected_status == '0':
                expected_status = 'offline'
            
            cursor.execute("SELECT id, name, status, last_updated FROM plants WHERE id = %s", (plant_id,))
            db_plant = cursor.fetchone()
            self.assertIsNotNone(db_plant)
            
            # Verify each field matches what we expect
            db_id, db_name, db_status, db_last_updated = db_plant
            self.assertEqual(db_id, plant_id, "Plant ID doesn't match")
            self.assertEqual(db_name, plant_name, "Plant name doesn't match")
            self.assertEqual(db_status, expected_status, "Plant status doesn't match")
            self.assertIsNotNone(db_last_updated, "Last updated timestamp not set")
            
            # Verify timestamp is recent (within last minute)
            time_diff = datetime.now() - db_last_updated
            self.assertLess(time_diff.total_seconds(), 60, "Last updated timestamp not recent")
            
            print(f"Successfully verified plant data in database: {plant_id}")
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Failed to save plants: {e}")
            raise
        finally:
            if conn:
                conn.close()


if __name__ == '__main__':
    unittest.main()