"""Dictionary management module for custom word mappings."""

import os
import csv
from typing import Dict, Tuple, List


class DictionaryManager:
    """Manages custom word dictionary with CSV file persistence."""
    
    def __init__(self, csv_path: str):
        """Initialize dictionary manager.
        
        Args:
            csv_path: Path to the CSV file containing custom words
        """
        self.csv_path = csv_path
        self.custom_dict: Dict[str, str] = {}
        self.file_mtime = 0
        self.load_dictionary()
    
    def load_dictionary(self) -> None:
        """Load custom dictionary from CSV file."""
        if os.path.exists(self.csv_path):
            try:
                # Check if file has been modified
                current_mtime = os.path.getmtime(self.csv_path)
                if current_mtime != self.file_mtime:
                    self.custom_dict.clear()
                    with open(self.csv_path, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        for row in reader:
                            if len(row) >= 2:
                                self.custom_dict[row[0].lower()] = row[1]
                    self.file_mtime = current_mtime
            except Exception as e:
                print(f"Warning: Could not load custom dictionary: {e}")
    
    def get(self, word: str) -> str:
        """Get the katakana reading for a word.
        
        Args:
            word: The word to look up
            
        Returns:
            The katakana reading if found, otherwise None
        """
        return self.custom_dict.get(word.lower())
    
    def add_entry(self, english: str, katakana: str) -> Tuple[bool, str]:
        """Add or update a dictionary entry.
        
        Args:
            english: The English word or phrase
            katakana: The katakana reading
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate inputs
            if not english or not katakana:
                return False, "エラー: 英単語とカタカナの両方を指定してください"
            
            # Convert to lowercase for consistency
            english_lower = english.lower()
            
            # Update in-memory dictionary
            self.custom_dict[english_lower] = katakana
            
            # Read existing entries
            existing_entries = []
            if os.path.exists(self.csv_path):
                with open(self.csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    existing_entries = list(reader)
            
            # Check if entry already exists and update it
            entry_updated = False
            for i, row in enumerate(existing_entries):
                if len(row) >= 2 and row[0].lower() == english_lower:
                    existing_entries[i] = [english_lower, katakana]
                    entry_updated = True
                    break
            
            # Add new entry if not updating
            if not entry_updated:
                existing_entries.append([english_lower, katakana])
            
            # Sort entries for better readability
            existing_entries.sort(key=lambda x: x[0] if x else '')
            
            # Write back to file
            with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(existing_entries)
            
            # Update modification time
            self.file_mtime = os.path.getmtime(self.csv_path)
            
            if entry_updated:
                return True, f"✓ 辞書を更新しました: {english_lower} → {katakana}"
            else:
                return True, f"✓ 辞書に登録しました: {english_lower} → {katakana}"
                
        except Exception as e:
            return False, f"エラー: 辞書への登録に失敗しました - {str(e)}"
    
    def remove_entry(self, english: str) -> Tuple[bool, str]:
        """Remove a dictionary entry.
        
        Args:
            english: The English word to remove
            
        Returns:
            Tuple of (success, message)
        """
        try:
            english_lower = english.lower()
            
            # Remove from in-memory dictionary
            if english_lower in self.custom_dict:
                del self.custom_dict[english_lower]
            else:
                return False, f"エラー: '{english}' は辞書に登録されていません"
            
            # Read and update file
            existing_entries = []
            if os.path.exists(self.csv_path):
                with open(self.csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2 and row[0].lower() != english_lower:
                            existing_entries.append(row)
            
            # Write back to file
            with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(existing_entries)
            
            # Update modification time
            self.file_mtime = os.path.getmtime(self.csv_path)
            
            return True, f"✓ 辞書から削除しました: {english_lower}"
            
        except Exception as e:
            return False, f"エラー: 辞書からの削除に失敗しました - {str(e)}"
    
    def list_entries(self) -> str:
        """List all dictionary entries.
        
        Returns:
            Formatted string of all entries
        """
        try:
            if not self.custom_dict:
                return "辞書は空です"
            
            # Sort entries for display
            sorted_entries = sorted(self.custom_dict.items())
            
            # Format as a nice list
            result = "カスタム辞書の内容:\n\n"
            for english, katakana in sorted_entries:
                result += f"  {english} → {katakana}\n"
            
            result += f"\n合計: {len(sorted_entries)} エントリ"
            return result
            
        except Exception as e:
            return f"エラー: 辞書の読み込みに失敗しました - {str(e)}"