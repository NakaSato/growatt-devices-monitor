    def get_device_notification_history(self, device_serial: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get notification history for a device
        
        Args:
            device_serial: The serial number of the device
            limit: Maximum number of records to return
            
        Returns:
            List[Dict[str, Any]]: List of notification history records
        """
        if not self.db:
            logger.warning("Database not available for notification history")
            return []
            
        try:
            query = """
                SELECT device_serial_number, notification_type, sent_at, message, success
                FROM notification_history
                WHERE device_serial_number = %s
                ORDER BY sent_at DESC
                LIMIT %s
            """
            
            return self.db.query(query, (device_serial, limit))
            
        except Exception as e:
            logger.error(f"Error retrieving notification history: {e}")
            return []
