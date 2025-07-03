#!/usr/bin/env python3
"""
Daily Odin Report Generator for BroadWorks System
================================================

This comprehensive script provides functionality for:
1. Daily Call Report Generation - fetches call records from all Service Providers
2. Global User Data Extraction - extracts comprehensive user data from all Service Providers
3. Data aggregation, processing, and export via SFTP and email

Author: AI Assistant
Version: 2.0.0
"""

import os
import sys
import json
import logging
import smtplib
import paramiko
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dataclasses import dataclass, field
from pathlib import Path
import time
import csv
from io import StringIO

# Configuration
@dataclass
class Config:
    # API Configuration
    api_base_url: str = os.getenv('ODIN_API_BASE_URL', '')
    api_username: str = os.getenv('ODIN_API_USERNAME', '')
    api_password: str = os.getenv('ODIN_API_PASSWORD', '')
    
    # Date range for call records (default: yesterday)
    start_date: str = os.getenv('REPORT_START_DATE', '')
    end_date: str = os.getenv('REPORT_END_DATE', '')
    
    # SFTP Configuration
    sftp_host: str = os.getenv('SFTP_HOST', '')
    sftp_port: int = int(os.getenv('SFTP_PORT', '22'))
    sftp_username: str = os.getenv('SFTP_USERNAME', '')
    sftp_password: str = os.getenv('SFTP_PASSWORD', '')
    sftp_remote_path: str = os.getenv('SFTP_REMOTE_PATH', '/reports/')
    
    # Email Configuration
    smtp_host: str = os.getenv('SMTP_HOST', '')
    smtp_port: int = int(os.getenv('SMTP_PORT', '587'))
    smtp_username: str = os.getenv('SMTP_USERNAME', '')
    smtp_password: str = os.getenv('SMTP_PASSWORD', '')
    smtp_from: str = os.getenv('SMTP_FROM', '')
    smtp_to: List[str] = field(
        default_factory=lambda: [
            a.strip() for a in os.getenv('SMTP_TO', '').split(',') if a.strip()
        ]
    )
    
    # Processing Configuration
    batch_size: int = int(os.getenv('BATCH_SIZE', '100'))
    max_retries: int = int(os.getenv('MAX_RETRIES', '3'))
    retry_delay: int = int(os.getenv('RETRY_DELAY', '5'))
    
    # Output Configuration
    output_dir: str = os.getenv('OUTPUT_DIR', './reports')
    
    # Global User Data Configuration
    include_optional_fields: bool = os.getenv('INCLUDE_OPTIONAL_FIELDS', 'true').lower() == 'true'

class OdinAPIClient:
    """
    Odin API Client for BroadWorks integration
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.token = None
        self.logger = logging.getLogger(__name__)
        
    def authenticate(self) -> bool:
        """
        Authenticate with the Odin API and obtain a bearer token
        """
        try:
            auth_url = f"{self.config.api_base_url}/api/v2/auth/token"
            auth_data = {
                'username': self.config.api_username,
                'password': self.config.api_password
            }
            
            response = self.session.post(auth_url, json=auth_data)
            response.raise_for_status()
            
            auth_result = response.json()
            self.token = auth_result.get('token')
            
            if self.token:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json'
                })
                self.logger.info("Successfully authenticated with Odin API")
                return True
            else:
                self.logger.error("No token received from authentication")
                return False
                
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def make_request(self, endpoint: str, params: Optional[Dict] = None, method: str = 'GET') -> Optional[Dict]:
        """
        Make a request to the Odin API with retry logic
        """
        url = f"{self.config.api_base_url}{endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params)
                elif method.upper() == 'POST':
                    response = self.session.post(url, json=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}/{self.config.max_retries}): {str(e)}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    self.logger.error(f"Request failed after {self.config.max_retries} attempts")
                    raise
    
    def get_service_providers(self) -> List[Dict]:
        """
        Fetch all Service Providers from the BroadWorks system
        """
        try:
            self.logger.info("Fetching service providers...")
            response = self.make_request('/api/v1/serviceproviders')
            
            if response and isinstance(response, list):
                self.logger.info(f"Found {len(response)} service providers")
                return response
            else:
                self.logger.warning("No service providers found or invalid response format")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to fetch service providers: {str(e)}")
            return []
    
    def get_groups_for_service_provider(self, service_provider_id: str) -> List[Dict]:
        """
        Fetch all groups for a specific Service Provider
        
        Args:
            service_provider_id (str): The service provider ID
            
        Returns:
            List[Dict]: List of group objects containing group information
        """
        try:
            self.logger.info(f"Fetching groups for service provider: {service_provider_id}")
            response = self.make_request(f'/api/v1/serviceproviders/{service_provider_id}/groups')
            
            if response and isinstance(response, list):
                self.logger.info(f"Found {len(response)} groups for service provider {service_provider_id}")
                return response
            else:
                self.logger.warning(f"No groups found for service provider {service_provider_id}")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to fetch groups for service provider {service_provider_id}: {str(e)}")
            return []
    
    def get_group_details(self, service_provider_id: str, group_id: str) -> Optional[Dict]:
        """
        Fetch detailed information for a specific group
        
        Args:
            service_provider_id (str): The service provider ID
            group_id (str): The group ID
            
        Returns:
            Optional[Dict]: Group details or None if not found
        """
        try:
            self.logger.info(f"Fetching details for group: {group_id}")
            response = self.make_request(f'/api/v1/serviceproviders/{service_provider_id}/groups/{group_id}')
            
            if response and isinstance(response, dict):
                self.logger.info(f"Successfully retrieved details for group {group_id}")
                return response
            else:
                self.logger.warning(f"No details found for group {group_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to fetch details for group {group_id}: {str(e)}")
            return None
    
    def get_users_for_group(self, service_provider_id: str, group_id: str) -> List[Dict]:
        """
        Fetch all users for a specific Group
        
        Args:
            service_provider_id (str): The service provider ID
            group_id (str): The group ID
            
        Returns:
            List[Dict]: List of user objects containing user information for the group
        """
        try:
            self.logger.info(f"Fetching users for group: {group_id}")
            response = self.make_request(f'/api/v1/serviceproviders/{service_provider_id}/groups/{group_id}/reports/users')
            
            if response and isinstance(response, list):
                self.logger.info(f"Found {len(response)} users for group {group_id}")
                return response
            else:
                self.logger.warning(f"No users found for group {group_id}")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to fetch users for group {group_id}: {str(e)}")
            return []
    
    def get_users_for_service_provider(self, service_provider_id: str) -> List[Dict]:
        """
        Fetch all users for a specific Service Provider
        """
        try:
            self.logger.info(f"Fetching users for service provider: {service_provider_id}")
            response = self.make_request(f'/api/v1/serviceproviders/{service_provider_id}/reports/users')
            
            if response and isinstance(response, list):
                self.logger.info(f"Found {len(response)} users for service provider {service_provider_id}")
                return response
            else:
                self.logger.warning(f"No users found for service provider {service_provider_id}")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to fetch users for service provider {service_provider_id}: {str(e)}")
            return []
    
    def get_user_report_for_service_provider(self, service_provider_id: str) -> List[Dict]:
        """
        Fetch detailed user report for a specific Service Provider
        This is equivalent to the 'Service Provider Users Report' but for a single SP
        
        Args:
            service_provider_id (str): The service provider ID
            
        Returns:
            List[Dict]: List of user objects with detailed information including:
                - Essential fields: userId, serviceProviderId, groupId, premiumServices, userServices, servicePacks
                - Optional fields: lastName, firstName, phoneNumber, extension, 
                  accessDeviceEndpoint.accessDevice.deviceType, networkClassOfService
        """
        try:
            self.logger.info(f"Fetching detailed user report for service provider: {service_provider_id}")
            response = self.make_request(f'/api/v1/serviceproviders/{service_provider_id}/reports/users')
            
            if response and isinstance(response, list):
                self.logger.info(f"Found {len(response)} users in detailed report for service provider {service_provider_id}")
                return response
            else:
                self.logger.warning(f"No users found in detailed report for service provider {service_provider_id}")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to fetch detailed user report for service provider {service_provider_id}: {str(e)}")
            return []
    
    def get_global_user_report(self) -> List[Dict]:
        """
        Fetch comprehensive user data from ALL Service Providers in the BroadWorks system
        This aggregates user data from all service providers into a single global report
        
        Returns:
            List[Dict]: List of user objects containing comprehensive user information from all service providers
        """
        try:
            self.logger.info("Fetching global user report from all service providers...")
            
            # Get all service providers first
            service_providers = self.get_service_providers()
            if not service_providers:
                self.logger.error("No service providers found for global user report")
                return []
            
            all_users = []
            
            # Fetch user data from each service provider
            for sp in service_providers:
                sp_id = sp.get('serviceProviderId')
                if not sp_id:
                    continue
                
                self.logger.info(f"Fetching user data for service provider: {sp_id}")
                
                # Get detailed user report for this service provider
                users = self.get_user_report_for_service_provider(sp_id)
                all_users.extend(users)
                
                # Add a small delay to avoid overwhelming the API
                time.sleep(0.5)
            
            self.logger.info(f"Global user report completed. Total users found: {len(all_users)}")
            return all_users
            
        except Exception as e:
            self.logger.error(f"Failed to fetch global user report: {str(e)}")
            return []
    
    def get_call_records_for_users(self, user_ids: List[str], start_time: str, end_time: str) -> List[Dict]:
        """
        Fetch call records for a list of users within a time range
        """
        try:
            self.logger.info(f"Fetching call records for {len(user_ids)} users")

            params = {
                'userIds':   user_ids,
                'startTime': start_time,
                'endTime':   end_time
            }
            # Use POST to send a JSON body
            response = self.make_request(
                '/api/v2/users/call-records/details',
                params,
                method='POST'
            )

            # The v2 endpoint returns a dict {{ total, count, offset, data: [ … ] }}
            records = []
            if isinstance(response, dict) and 'data' in response:
                records = response['data']
            elif isinstance(response, list):
                # fallback if API ever returns a bare list
                records = response

            self.logger.info(f"Found {len(records)} call records")
            return records

        except Exception as e:
            self.logger.error(f"Failed to fetch call records: {{str(e)}}")
            return []

class CallRecordProcessor:
    """
    Process and aggregate call record data
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def process_call_records(self, raw_records: List[Dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Process raw call records and return both raw and aggregated DataFrames
        """
        if not raw_records:
            return pd.DataFrame(), pd.DataFrame()
        
        # Convert to DataFrame
        df_raw = pd.DataFrame(raw_records)
        
        # Clean and standardize the data
        df_clean = self._clean_call_records(df_raw)
        
        # Generate aggregated metrics
        df_aggregated = self._aggregate_by_service_provider(df_clean)
        
        return df_clean, df_aggregated
    
    def _clean_call_records(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and standardize call record data
        """
        try:
            # Ensure required columns exist
            required_columns = [
                'serviceProviderId', 'userId', 'callingNumber', 'calledNumber',
                'startTime', 'answerTime', 'releaseTime', 'totalSeconds',
                'placedSeconds', 'waitSeconds', 'answerIndicator', 'direction'
            ]
            
            for col in required_columns:
                if col not in df.columns:
                    df[col] = None
            
            # Convert time columns to datetime
            time_columns = ['startTime', 'answerTime', 'releaseTime']
            for col in time_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Convert duration columns to numeric
            duration_columns = ['totalSeconds', 'placedSeconds', 'waitSeconds']
            for col in duration_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    df[col] = df[col].fillna(0)
            
            # Add calculated fields
            df['call_date'] = df['startTime'].dt.date
            df['call_hour'] = df['startTime'].dt.hour
            df['answered'] = df['answerIndicator'].isin(['Yes', 'Yes-PostRedirection'])
            df['call_type'] = df.apply(self._determine_call_type, axis=1)
            
            self.logger.info(f"Cleaned {len(df)} call records")
            return df
            
        except Exception as e:
            self.logger.error(f"Error cleaning call records: {str(e)}")
            return df
    
    def _determine_call_type(self, row) -> str:
        """
        Determine call type based on direction and answer indicator
        """
        direction = row.get('direction', '')
        answer_indicator = row.get('answerIndicator', '')
        
        if direction == 'Originating':
            return 'Outbound_Answered' if answer_indicator == 'Yes' else 'Outbound_Missed'
        elif direction == 'Terminating':
            return 'Inbound_Answered' if answer_indicator == 'Yes' else 'Inbound_Missed'
        else:
            return 'Unknown'
    
    def _aggregate_by_service_provider(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate call records by Service Provider
        """
        try:
            if df.empty:
                return pd.DataFrame()
            
            # Group by service provider and calculate metrics
            agg_data = df.groupby('serviceProviderId').agg({
                'userId': 'nunique',  # Unique users
                'callingNumber': 'count',  # Total calls
                'totalSeconds': ['sum', 'mean'],  # Total and average duration
                'placedSeconds': ['sum', 'mean'],
                'waitSeconds': ['sum', 'mean'],
                'answered': 'sum',  # Answered calls
                'call_date': ['min', 'max']  # Date range
            }).round(2)
            
            # Flatten column names
            agg_data.columns = ['_'.join(col).strip() if col[1] else col[0] for col in agg_data.columns]
            
            # Calculate additional metrics
            agg_data['total_calls'] = agg_data['callingNumber_count']
            agg_data['answered_calls'] = agg_data['answered_sum']
            agg_data['missed_calls'] = agg_data['total_calls'] - agg_data['answered_calls']
            agg_data['answer_rate'] = (agg_data['answered_calls'] / agg_data['total_calls'] * 100).round(2)
            
            # Add call type breakdown
            call_type_breakdown = df.groupby(['serviceProviderId', 'call_type']).size().unstack(fill_value=0)
            agg_data = agg_data.join(call_type_breakdown, how='left')
            
            # Reset index to make serviceProviderId a column
            agg_data.reset_index(inplace=True)
            
            # Add report generation timestamp
            agg_data['report_generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.logger.info(f"Generated aggregated data for {len(agg_data)} service providers")
            return agg_data
            
        except Exception as e:
            self.logger.error(f"Error aggregating data: {str(e)}")
            return pd.DataFrame()

class GlobalUserDataProcessor:
    """
    Process and clean global user data
    """
    
    def __init__(self, include_optional_fields: bool = True):
        self.include_optional_fields = include_optional_fields
        self.logger = logging.getLogger(__name__)
    
    def process_user_data(self, raw_users: List[Dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Process raw user data and return both detailed and summary DataFrames
        """
        if not raw_users:
            return pd.DataFrame(), pd.DataFrame()
        
        # Convert to DataFrame
        df_raw = pd.DataFrame(raw_users)
        
        # Clean and standardize the data
        df_clean = self._clean_user_data(df_raw)
        
        # Generate summary metrics
        df_summary = self._create_summary_report(df_clean)
        
        return df_clean, df_summary
    
    def _clean_user_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and standardize user data
        """
        try:
            # Essential fields (always included) - as specified in requirements
            essential_fields = [
                'userId', 'serviceProviderId', 'groupId', 
                'premiumServices', 'userServices', 'servicePacks'
            ]
            
            # Optional fields (nice-to-have) - as specified in requirements
            optional_fields = [
                'lastName', 'firstName', 'phoneNumber', 'extension',
                'networkClassOfService'
            ]
            
            # Additional optional fields for enhanced reporting
            additional_optional_fields = [
                'emailAddress', 'timeZone', 'userType', 'isActive', 
                'department', 'title'
            ]
            
            # Ensure essential columns exist
            for col in essential_fields:
                if col not in df.columns:
                    df[col] = None
            
            # Add optional fields if configured
            if self.include_optional_fields:
                for col in optional_fields + additional_optional_fields:
                    if col not in df.columns:
                        df[col] = None
            
            # Extract device information from accessDeviceEndpoint
            df = self._extract_device_info(df)
            
            # Add calculated fields
            for col in ['firstName', 'lastName']:
                if col not in df.columns:
                    df[col] = ''
            df['full_name'] = (
                df['firstName'].fillna('').astype(str) + ' ' +
                df['lastName'].fillna('').astype(str)
            ).str.strip()
            df['is_active'] = df.get('isActive', False)
            if 'emailAddress' not in df.columns:
                df['emailAddress'] = ''
            df['has_email'] = df['emailAddress'].notna() & (df['emailAddress'] != '')
            for col in ['phoneNumber', 'extension']:
                if col not in df.columns:
                    df[col] = ''
            df['has_phone'] = df['phoneNumber'].notna() & (df['phoneNumber'] != '')
            df['has_extension'] = df['extension'].notna() & (df['extension'] != '')
            
            # Convert service lists to strings for CSV compatibility
            for service_col in ['premiumServices', 'userServices', 'servicePacks']:
                if service_col in df.columns:
                    df[service_col] = df[service_col].apply(
                        lambda x: '; '.join(x) if isinstance(x, list) else str(x) if x else ''
                    )
            
            # Add report generation timestamp
            df['report_generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.logger.info(f"Cleaned {len(df)} user records")
            return df
            
        except Exception as e:
            self.logger.error(f"Error cleaning user data: {str(e)}")
            return df
    
    def _extract_device_info(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract device information from nested JSON structures
        Specifically handles accessDeviceEndpoint.accessDevice.deviceType as requested
        """
        try:
            # Extract device type from accessDeviceEndpoint - this is the specific field requested
            if 'accessDeviceEndpoint' in df.columns and self.include_optional_fields:
                df['device_type'] = df['accessDeviceEndpoint'].apply(
                    lambda x: x.get('accessDevice', {}).get('deviceType', '') if isinstance(x, dict) else ''
                )
                df['device_name'] = df['accessDeviceEndpoint'].apply(
                    lambda x: x.get('accessDevice', {}).get('deviceName', '') if isinstance(x, dict) else ''
                )
                df['line_port'] = df['accessDeviceEndpoint'].apply(
                    lambda x: x.get('linePort', '') if isinstance(x, dict) else ''
                )
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error extracting device info: {str(e)}")
            return df
    
    def _create_summary_report(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create summary report by Service Provider and Group
        """
        try:
            if df.empty:
                return pd.DataFrame()
            
            # Convert boolean columns to integers   
            for col in ['is_active', 'has_email', 'has_phone', 'has_extension']:
                if col in df.columns:
                    df[col] = df[col].astype(bool).astype(int)
            
            # Summary by Service Provider
            sp_summary = df.groupby('serviceProviderId').agg({
                'userId': 'nunique',  # Unique users
                'is_active': 'sum',   # Active users
                'has_email': 'sum',   # Users with email
                'has_phone': 'sum',   # Users with phone
                'has_extension': 'sum', # Users with extension
                'groupId': 'nunique'  # Unique groups
            }).round(2)
            
            # Rename columns for clarity
            sp_summary.columns = [
                'total_users', 'active_users', 'users_with_email', 
                'users_with_phone', 'users_with_extension', 'total_groups'
            ]
            
            # Calculate percentages
            sp_summary['active_percentage'] = (sp_summary['active_users'] / sp_summary['total_users'] * 100).round(2)
            sp_summary['email_percentage'] = (sp_summary['users_with_email'] / sp_summary['total_users'] * 100).round(2)
            
            # Reset index to make serviceProviderId a column
            sp_summary.reset_index(inplace=True)
            
            # Add report generation timestamp
            sp_summary['report_generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.logger.info(f"Generated summary data for {len(sp_summary)} service providers")
            
            if isinstance(sp_summary, pd.Series):
                sp_summary = sp_summary.to_frame().T
            
            return sp_summary
            
        except Exception as e:
            self.logger.error(f"Error creating summary report: {str(e)}")
            return pd.DataFrame()

class ReportExporter:
    """
    Export reports via SFTP and email
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def export_to_csv(self, df_raw: pd.DataFrame, df_aggregated: pd.DataFrame) -> tuple[str, str]:
        """
        Export DataFrames to CSV files
        """
        try:
            # Create output directory
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate timestamps for filenames
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Export raw data
            raw_filename = f"raw_user_calls_{timestamp}.csv"
            raw_filepath = output_dir / raw_filename
            df_raw.to_csv(raw_filepath, index=False)
            
            # Export aggregated data
            agg_filename = f"aggregated_by_service_provider_{timestamp}.csv"
            agg_filepath = output_dir / agg_filename
            df_aggregated.to_csv(agg_filepath, index=False)
            
            self.logger.info(f"Exported CSV files: {raw_filename}, {agg_filename}")
            return str(raw_filepath), str(agg_filepath)
            
        except Exception as e:
            self.logger.error(f"Error exporting CSV files: {str(e)}")
            raise
    
    def export_user_data_to_csv(self, df_users: pd.DataFrame, df_summary: pd.DataFrame) -> tuple[str, str]:
        """
        Export user data DataFrames to CSV files
        """
        try:
            # Create output directory
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate timestamps for filenames
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            exported_files = []
            
            # Export user data
            users_filename = f"global_user_data_{timestamp}.csv"
            users_filepath = output_dir / users_filename
            df_users.to_csv(users_filepath, index=False)
            exported_files.append(str(users_filepath))
            
            # Export summary data
            summary_filename = f"user_summary_by_service_provider_{timestamp}.csv"
            summary_filepath = output_dir / summary_filename
            df_summary.to_csv(summary_filepath, index=False)
            exported_files.append(str(summary_filepath))
            
            self.logger.info(f"Exported CSV files: {users_filename}, {summary_filename}")
            return str(users_filepath), str(summary_filepath)
            
        except Exception as e:
            self.logger.error(f"Error exporting CSV files: {str(e)}")
            raise
    
    def upload_to_sftp(self, local_files: List[str]) -> bool:
        """
        Upload files to SFTP server
        """
        try:
            # Create SFTP connection
            transport = paramiko.Transport((self.config.sftp_host, self.config.sftp_port))
            transport.connect(username=self.config.sftp_username, password=self.config.sftp_password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            
            if sftp is None:
                self.logger.error("Failed to establish SFTP connection")
                transport.close()
                return False
            
            # Now safe to use sftp.put
            for local_file in local_files:
                local_path = Path(local_file)
                remote_path = f"{self.config.sftp_remote_path.rstrip('/')}/{local_path.name}"
                sftp.put(local_file, remote_path)
                self.logger.info(f"Uploaded {local_path.name} to SFTP server")
            
            # Close connection
            sftp.close()
            transport.close()
            
            self.logger.info("Successfully uploaded all files to SFTP server")
            return True
            
        except Exception as e:
            self.logger.error(f"Error uploading to SFTP: {str(e)}")
            return False
    
    def send_email_report(self, csv_files: List[str], summary_stats: Dict) -> bool:
        """
        Send email report with CSV attachments
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.smtp_from
            msg['To'] = ', '.join(self.config.smtp_to)
            msg['Subject'] = f"Daily Odin Report - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Create email body
            body = self._create_email_body(summary_stats)
            msg.attach(MIMEText(body, 'html'))
            
            # Attach CSV files
            for csv_file in csv_files:
                self._attach_file(msg, csv_file)
            
            # Send email
            server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
            server.starttls()
            server.login(self.config.smtp_username, self.config.smtp_password)
            
            text = msg.as_string()
            server.sendmail(self.config.smtp_from, self.config.smtp_to, text)
            server.quit()
            
            self.logger.info("Email report sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email: {str(e)}")
            return False
    
    def _create_email_body(self, summary_stats: Dict) -> str:
        """
        Create HTML email body with summary statistics
        """
        html_body = f"""
        <html>
        <head></head>
        <body>
            <h2>Daily Odin Report Summary</h2>
            <p>Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h3>Overall Statistics</h3>
            <ul>
                <li>Total Service Providers: {summary_stats.get('total_service_providers', 0)}</li>
                <li>Total Users: {summary_stats.get('total_users', 0)}</li>
                <li>Total Calls: {summary_stats.get('total_calls', 0):,}</li>
                <li>Total Call Duration: {summary_stats.get('total_duration_hours', 0):.2f} hours</li>
                <li>Average Call Duration: {summary_stats.get('avg_duration_seconds', 0):.2f} seconds</li>
                <li>Answer Rate: {summary_stats.get('overall_answer_rate', 0):.2f}%</li>
            </ul>
            
            <h3>Attached Files</h3>
            <ul>
                <li><strong>raw_user_calls.csv</strong> - Detailed call records for all users</li>
                <li><strong>aggregated_by_service_provider.csv</strong> - Summary metrics by Service Provider</li>
            </ul>
            
            <p>This report was generated automatically by the Daily Odin Report system.</p>
        </body>
        </html>
        """
        return html_body
    
    def _attach_file(self, msg: MIMEMultipart, filepath: str):
        """
        Attach a file to the email message
        """
        with open(filepath, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {Path(filepath).name}'
        )
        msg.attach(part)

class DailyCallReportGenerator:
    """
    Main class orchestrating the daily call report generation
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = self._setup_logging()
        self.api_client = OdinAPIClient(config)
        self.processor = CallRecordProcessor(config)
        self.exporter = ReportExporter(config)
    
    def _setup_logging(self) -> logging.Logger:
        """
        Set up logging configuration
        """
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create file handler
        log_file = Path(self.config.output_dir) / 'daily_call_report.log'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def _get_date_range(self) -> tuple[str, str]:
        """
        Get the date range for the report
        """
        if self.config.start_date and self.config.end_date:
            return self.config.start_date, self.config.end_date
        
        # Default to yesterday
        yesterday = datetime.now() - timedelta(days=1)
        start_date = yesterday.strftime('%Y-%m-%d 00:00:00')
        end_date = yesterday.strftime('%Y-%m-%d 23:59:59')
        
        return start_date, end_date
    
    def run(self) -> bool:
        """
        Execute the complete daily call report generation process
        """
        try:
            self.logger.info("Starting daily call report generation...")
            
            # Step 1: Authenticate with API
            if not self.api_client.authenticate():
                self.logger.error("Failed to authenticate with Odin API")
                return False
            
            # Step 2: Get date range
            start_date, end_date = self._get_date_range()
            self.logger.info(f"Generating report for period: {start_date} to {end_date}")
            
            # Step 3: Fetch all service providers
            service_providers = self.api_client.get_service_providers()
            if not service_providers:
                self.logger.error("No service providers found")
                return False
            
            # Step 4: Process each service provider
            all_call_records = []
            total_users = 0
            
            for sp in service_providers:
                sp_id = sp.get('serviceProviderId')
                if not sp_id:
                    continue
                
                self.logger.info(f"Processing service provider: {sp_id}")
                
                # Get users for this service provider
                users = self.api_client.get_users_for_service_provider(sp_id)
                total_users += len(users)
                
                if not users:
                    continue
                
                # Process users in batches
                user_ids = [str(user.get('userId')) for user in users if user.get('userId') is not None]
                
                for i in range(0, len(user_ids), self.config.batch_size):
                    batch_user_ids = user_ids[i:i + self.config.batch_size]
                    call_records = self.api_client.get_call_records_for_users(
                        batch_user_ids, start_date, end_date
                    )
                    all_call_records.extend(call_records)
            
            # Step 5: Process and aggregate data
            self.logger.info(f"Processing {len(all_call_records)} call records...")
            df_raw, df_aggregated = self.processor.process_call_records(all_call_records)
            
            if df_raw.empty:
                self.logger.warning("No call records to process")
                return False
            
            # Step 6: Export to CSV
            raw_csv, agg_csv = self.exporter.export_to_csv(df_raw, df_aggregated)
            csv_files = [raw_csv, agg_csv]
            
            # Step 7: Upload to SFTP
            if self.config.sftp_host:
                self.exporter.upload_to_sftp(csv_files)
            
            # Step 8: Send email report
            if self.config.smtp_host:
                summary_stats = self._calculate_summary_stats(df_raw, df_aggregated, len(service_providers), total_users)
                self.exporter.send_email_report(csv_files, summary_stats)
            
            self.logger.info("Daily call report generation completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during report generation: {str(e)}")
            return False
    
    def _calculate_summary_stats(self, df_raw: pd.DataFrame, df_aggregated: pd.DataFrame, 
                                total_sp: int, total_users: int) -> Dict:
        """
        Calculate summary statistics for the email report
        """
        return {
            'total_service_providers': total_sp,
            'total_users': total_users,
            'total_calls': len(df_raw),
            'total_duration_hours': df_raw['totalSeconds'].sum() / 3600,
            'avg_duration_seconds': df_raw['totalSeconds'].mean(),
            'overall_answer_rate': (df_raw['answered'].sum() / len(df_raw) * 100) if len(df_raw) > 0 else 0
        }

class GlobalUserDataExtractor:
    """
    Main class for extracting global user data
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = self._setup_logging()
        self.api_client = OdinAPIClient(config)
        self.processor = GlobalUserDataProcessor(
            include_optional_fields=getattr(config, 'include_optional_fields', True)
        )
        self.exporter = ReportExporter(config)
    
    def _setup_logging(self) -> logging.Logger:
        """
        Set up logging configuration
        """
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create file handler
        log_file = Path(self.config.output_dir) / 'global_user_data.log'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def run(self) -> bool:
        """
        Execute the complete global user data extraction process
        """
        try:
            self.logger.info("Starting global user data extraction...")
            
            # Step 1: Authenticate with API
            if not self.api_client.authenticate():
                self.logger.error("Failed to authenticate with Odin API")
                return False
            
            # Step 2: Extract global user data
            self.logger.info("Extracting global user data...")
            all_users = self.api_client.get_global_user_report()
            
            if not all_users:
                self.logger.warning("No user data extracted")
                return False
            
            # Step 3: Process and clean data
            self.logger.info(f"Processing {len(all_users)} user records...")
            df_users, df_summary = self.processor.process_user_data(all_users)
            
            if df_users.empty:
                self.logger.warning("No user data to process")
                return False
            
            # Step 4: Export to CSV
            csv_files = self._export_to_csv(df_users, df_summary)
            
            # Step 5: Upload to SFTP (if configured)
            if self.config.sftp_host:
                self.exporter.upload_to_sftp(csv_files)
            
            # Step 6: Send email report (if configured)
            if self.config.smtp_host:
                summary_stats = self._calculate_summary_stats(df_users, df_summary)
                self.exporter.send_email_report(csv_files, summary_stats)
            
            self.logger.info("Global user data extraction completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during global user data extraction: {str(e)}")
            return False
    
    def _export_to_csv(self, df_users: pd.DataFrame, df_summary: pd.DataFrame) -> List[str]:
        """
        Export DataFrames to CSV files
        """
        try:
            # Create output directory
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate timestamps for filenames
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            exported_files = []
            
            # Export user data
            users_filename = f"global_user_data_{timestamp}.csv"
            users_filepath = output_dir / users_filename
            df_users.to_csv(users_filepath, index=False)
            exported_files.append(str(users_filepath))
            
            # Export summary data
            summary_filename = f"user_summary_by_service_provider_{timestamp}.csv"
            summary_filepath = output_dir / summary_filename
            df_summary.to_csv(summary_filepath, index=False)
            exported_files.append(str(summary_filepath))
            
            self.logger.info(f"Exported CSV files: {users_filename}, {summary_filename}")
            return exported_files
            
        except Exception as e:
            self.logger.error(f"Error exporting CSV files: {str(e)}")
            raise
    
    def _calculate_summary_stats(self, df_users: pd.DataFrame, df_summary: pd.DataFrame) -> Dict:
        """
        Calculate summary statistics for the email report
        """
        return {
            'total_service_providers': len(df_summary) if not df_summary.empty else 0,
            'total_groups': df_users['groupId'].nunique() if 'groupId' in df_users.columns else 0,
            'total_users': len(df_users),
            'active_users': df_users['is_active'].sum() if 'is_active' in df_users.columns else 0,
            'users_with_email': df_users['has_email'].sum() if 'has_email' in df_users.columns else 0,
            'users_with_phone': df_users['has_phone'].sum() if 'has_phone' in df_users.columns else 0,
            'users_with_extension': df_users['has_extension'].sum() if 'has_extension' in df_users.columns else 0,
        }

def main():
    """
    Main entry point for the script
    """
    try:
        # Load configuration
        config = Config()
        
        # Validate required configuration
        required_fields = ['api_base_url', 'api_username', 'api_password']
        missing_fields = [field for field in required_fields if not getattr(config, field)]
        
        if missing_fields:
            print(f"Error: Missing required configuration: {', '.join(missing_fields)}")
            sys.exit(1)
        
        # Run the report generator
        generator = DailyCallReportGenerator(config)
        success = generator.run()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nReport generation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 