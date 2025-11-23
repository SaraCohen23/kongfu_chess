import pygame
import os
from typing import Dict, Optional

class SoundManager:
    """Manages sound effects for the KFC game."""
    
    def __init__(self, sound_dir: str = "sound"):
        """Initialize the sound manager.
        
        Args:
            sound_dir: Directory containing sound files relative to this module
        """
        self.sound_dir = sound_dir
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.enabled = True
        
        # Initialize pygame mixer
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self._load_sounds()
        except Exception as e:
            self.enabled = False
    
    def _load_sounds(self):
        """Load all sound files from the sound directory."""
        base_path = os.path.dirname(os.path.abspath(__file__))
        sound_path = os.path.join(base_path, self.sound_dir)
        
        if not os.path.exists(sound_path):
            self.enabled = False
            return
        
        # Define sound mappings
        sound_files = {
            'move': 'move.wav',
            'eat': 'eat.wav', 
            'tada': 'TADA.WAV'
        }
        
        for sound_name, filename in sound_files.items():
            file_path = os.path.join(sound_path, filename)
            if os.path.exists(file_path):
                try:
                    self.sounds[sound_name] = pygame.mixer.Sound(file_path)
                except Exception as e:
                    pass  # Silent fail
            else:
                pass  # File not found
    
    def play_move(self):
        """Play the move sound effect."""
        self._play_sound('move')
    
    def play_eat(self):
        """Play the eat/capture sound effect."""
        self._play_sound('eat')
    
    def play_victory(self):
        """Play the victory/tada sound effect."""
        self._play_sound('tada')
    
    def _play_sound(self, sound_name: str):
        """Play a specific sound by name."""
        if not self.enabled:
            return
            
        if sound_name in self.sounds:
            try:
                self.sounds[sound_name].play()
            except Exception as e:
                pass  # Silent fail
    
    def set_volume(self, volume: float):
        """Set volume for all sounds (0.0 to 1.0)."""
        if not self.enabled:
            return
            
        for sound in self.sounds.values():
            sound.set_volume(volume)
    
    def enable_sound(self, enabled: bool):
        """Enable or disable sound effects."""
        self.enabled = enabled
