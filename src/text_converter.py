"""Text conversion module for converting text to katakana."""

import re
from typing import Tuple, List, Optional
from .dictionary_manager import DictionaryManager

try:
    import alkana
except ImportError:
    alkana = None


class TextConverter:
    """Converts text including English, numbers, and Japanese to appropriate katakana."""
    
    def __init__(self, dictionary_manager: DictionaryManager):
        """Initialize text converter.
        
        Args:
            dictionary_manager: Instance of DictionaryManager for custom words
        """
        self.dict_manager = dictionary_manager
    
    def convert_to_katakana(self, text: str) -> Tuple[str, List[str]]:
        """Convert text to katakana using custom dictionary and alkana.
        
        This method now supports:
        - English words and phrases
        - File extensions (e.g., .py, .csv)
        - Numbers with Japanese text (e.g., 2つ, 3個)
        - Mixed patterns
        
        Args:
            text: Text to convert
            
        Returns:
            Tuple of (converted_text, unconverted_words)
        """
        # Reload dictionary to get latest changes
        self.dict_manager.load_dictionary()
        
        if not alkana and not self.dict_manager.custom_dict:
            return text, []
        
        # Enhanced tokenization pattern that captures:
        # - File names with extensions (e.g., "main.py")
        # - Extensions alone (e.g., ".py")
        # - English words
        # - Numbers with optional Japanese suffix (e.g., "2つ", "3個")
        # - Japanese text (hiragana, katakana, kanji)
        # - Other characters
        tokens = re.findall(
            r'[A-Za-z]+\.[A-Za-z]+|'  # Files with extensions
            r'\.[A-Za-z]+|'            # Extensions only
            r'[A-Za-z]+|'              # English words
            r'\d+[つ個枚本件度回目番月日年時分秒]?|'  # Numbers with optional counters
            r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+|'  # Japanese
            r'[^\w\s]|'                # Punctuation
            r'\s+',                    # Whitespace
            text
        )
        
        converted_tokens = []
        unconverted_words = []
        
        # Process tokens
        i = 0
        while i < len(tokens):
            token = tokens[i]
            converted = False
            
            # First, check if this token (or combination) is in the dictionary
            # Try longer combinations first (for cases like "2つ目")
            for length in range(min(3, len(tokens) - i), 0, -1):
                combined_token = ''.join(tokens[i:i+length])
                if self.dict_manager.get(combined_token):
                    converted_tokens.append(self.dict_manager.get(combined_token))
                    i += length
                    converted = True
                    break
            
            if converted:
                continue
            
            # Handle file names with extensions
            if re.match(r'^[A-Za-z]+\.[A-Za-z]+$', token):
                parts = token.split('.')
                base_word = parts[0]
                extension = '.' + parts[1]
                
                # Check if full filename is in dictionary
                if self.dict_manager.get(token):
                    converted_tokens.append(self.dict_manager.get(token))
                # Check if extension is in dictionary
                elif self.dict_manager.get(extension):
                    # Convert base word
                    base_converted = self._convert_single_word(base_word)
                    converted_tokens.append(base_converted[0])
                    if base_converted[1]:
                        unconverted_words.extend(base_converted[1])
                    # Add extension from dictionary
                    converted_tokens.append(self.dict_manager.get(extension))
                else:
                    # Convert as single token
                    result = self._convert_single_word(token)
                    converted_tokens.append(result[0])
                    if result[1]:
                        unconverted_words.extend(result[1])
            else:
                # Convert single token
                result = self._convert_single_word(token)
                converted_tokens.append(result[0])
                if result[1]:
                    unconverted_words.extend(result[1])
            
            i += 1
        
        return ''.join(converted_tokens), unconverted_words
    
    def _convert_single_word(self, word: str) -> Tuple[str, List[str]]:
        """Convert a single word to katakana.
        
        Args:
            word: Word to convert
            
        Returns:
            Tuple of (converted_word, [unconverted_word] or [])
        """
        # Check if it's a convertible pattern (English, numbers, etc.)
        if not re.match(r'^[\w\.]+$', word):
            # Not a word that needs conversion (punctuation, etc.)
            return word, []
        
        word_lower = word.lower()
        
        # First try custom dictionary
        if self.dict_manager.get(word_lower):
            return self.dict_manager.get(word_lower), []
        
        # For English words, try alkana
        if re.match(r'^[A-Za-z\.]+$', word) and alkana:
            katakana = alkana.get_kana(word_lower)
            if katakana:
                return katakana, []
        
        # If not converted, track it (but not Japanese text)
        if re.match(r'^[A-Za-z0-9\.]+', word):
            return word, [word_lower]
        
        # Return as-is for Japanese text
        return word, []