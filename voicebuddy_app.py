import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import threading
import time
import random
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
from typing import Dict, List, Optional
import difflib
import wave
import tempfile
import numpy as np
import sys
import traceback

def show_traceback(type, value, tb):
    traceback.print_exception(type, value, tb)
    input("Press Enter to close...")

sys.excepthook = show_traceback


# For speech functionality (install with: pip install openai-whisper pyttsx3 pyaudio soundfile)
try:
    import whisper
    import pyaudio
    import soundfile as sf
    import pyttsx3
    SPEECH_AVAILABLE = True
    print("Whisper and audio modules loaded successfully!")
except ImportError as e:
    SPEECH_AVAILABLE = False
    print(f"Speech modules not available. Install with: pip install openai-whisper pyttsx3 pyaudio soundfile\nError: {e}")

class VoiceBuddyAI:
    def __init__(self, root):
        self.root = root
        self.root.title("🗣️ VoiceBuddy AI - Speech Practice (Whisper Edition)")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Data storage
        self.data_file = "voicebuddy_data.json"
        self.settings_file = "voicebuddy_settings.json"
        self.load_data()
        
        # Speech components
        if SPEECH_AVAILABLE:
            # Initialize Whisper model (using base model for balance of speed/accuracy)
            self.whisper_model = None
            self.load_whisper_model()
            
            # Audio recording parameters
            self.audio_format = pyaudio.paInt16
            self.channels = 1
            self.rate = 16000  # Whisper works best with 16kHz
            self.chunk = 1024
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # TTS setup
            try:
                self.tts_engine = pyttsx3.init()
                self.setup_tts()
            except:
                self.tts_engine = None
                print("TTS engine could not be initialized")
        
        # Current session variables
        self.current_phrase = ""
        self.current_context = ""
        self.is_recording = False
        self.audio_frames = []
        
        # Create GUI
        self.create_widgets()
        self.update_stats()
        
        # AI API Configuration (you'll need to set your API key)
        self.api_key = "YOUR_ANTHROPIC_API_KEY"  # Replace with actual API key
        
    def load_whisper_model(self):
     try:
        print("Loading Whisper model... This may take a moment on first run.")
        model_size = self.settings.get('whisper_model_size', 'base')
        self.whisper_model = whisper.load_model(model_size)
        print(f"Whisper model '{model_size}' loaded successfully!")
     except Exception as e:
        print(f"Error loading Whisper model: {e}")
        self.whisper_model = None

        
    def load_data(self):
        """Load user data and settings"""
        try:
            with open(self.data_file, 'r') as f:
                self.user_data = json.load(f)
        except FileNotFoundError:
            self.user_data = {
                'sessions': [],
                'scores': [],
                'total_sessions': 0,
                'best_score': 0
            }
        
        try:
            with open(self.settings_file, 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {
                'focus_area': 'general',
                'difficulty_level': 'beginner',
                'topic_interest': '',
                'phrase_length': 'medium',
                'whisper_model_size': 'base'
            }
    
    def save_data(self):
        """Save user data and settings"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.user_data, f, indent=2)
            
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def setup_tts(self):
        """Configure text-to-speech engine"""
        if SPEECH_AVAILABLE and self.tts_engine:
            try:
                voices = self.tts_engine.getProperty('voices')
                if voices:
                    self.tts_engine.setProperty('voice', voices[0].id)
                self.tts_engine.setProperty('rate', 150)
                self.tts_engine.setProperty('volume', 0.8)
            except Exception as e:
                print(f"Error setting up TTS: {e}")
    
    def create_widgets(self):
        """Create the main GUI interface"""
        # Create main frames
        self.create_header()
        self.create_sidebar()
        self.create_main_content()
    
    def create_header(self):
        """Create header with title"""
        header_frame = tk.Frame(self.root, bg='#4f46e5', height=80)
        header_frame.pack(fill='x', padx=10, pady=(10, 0))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame, 
            text="🗣️ VoiceBuddy AI",
            font=("Arial", 24, "bold"),
            bg='#4f46e5',
            fg='white'
        )
        title_label.pack(expand=True)
        
        subtitle_label = tk.Label(
            header_frame,
            text="AI-Powered Speech Practice Assistant (Whisper Edition)",
            font=("Arial", 12),
            bg='#4f46e5',
            fg='#e0e7ff'
        )
        subtitle_label.pack()
    
    def create_sidebar(self):
        """Create sidebar with settings and navigation"""
        main_container = tk.Frame(self.root, bg='#f0f0f0')
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Sidebar
        sidebar_frame = tk.Frame(main_container, bg='white', width=300)
        sidebar_frame.pack(side='left', fill='y', padx=(0, 10))
        sidebar_frame.pack_propagate(False)
        
        # Settings section
        settings_label = tk.Label(
            sidebar_frame,
            text="🎯 Practice Settings",
            font=("Arial", 14, "bold"),
            bg='white',
            fg='#374151'
        )
        settings_label.pack(pady=(20, 10), padx=20, anchor='w')
        
        # Focus Area
        self.create_setting_dropdown(
            sidebar_frame, "Focus Area:", 'focus_area',
            ["general", "pronunciation", "articulation", "fluency", 
             "consonants", "vowels", "tongue_twisters"]
        )
        
        # Difficulty Level
        self.create_setting_dropdown(
            sidebar_frame, "Difficulty Level:", 'difficulty_level',
            ["beginner", "intermediate", "advanced", "adaptive"]
        )
        
        # Whisper Model Size
        self.create_setting_dropdown(
            sidebar_frame, "Whisper Model:", 'whisper_model_size',
            ["tiny", "base", "small", "medium"]
        )
        
        # Topic Interest
        self.create_setting_entry(
            sidebar_frame, "Topic Interest:", 'topic_interest',
            "e.g., animals, technology, sports"
        )
        
        # Phrase Length
        self.create_setting_dropdown(
            sidebar_frame, "Phrase Length:", 'phrase_length',
            ["short", "medium", "long"]
        )
        
        # Model status indicator
        self.model_status_label = tk.Label(
            sidebar_frame,
            text="🔄 Loading Whisper model...",
            font=("Arial", 9),
            bg='white',
            fg='#666'
        )
        self.model_status_label.pack(pady=(10, 0), padx=20)
        
        # Update model status periodically
        self.check_model_status()
        
        # Stats section
        stats_label = tk.Label(
            sidebar_frame,
            text="📊 Quick Stats",
            font=("Arial", 14, "bold"),
            bg='white',
            fg='#374151'
        )
        stats_label.pack(pady=(30, 10), padx=20, anchor='w')
        
        self.stats_frame = tk.Frame(sidebar_frame, bg='white')
        self.stats_frame.pack(fill='x', padx=20)
        
        # Store references to main container for main content
        self.main_container = main_container
    
    def check_model_status(self):
        """Check and update Whisper model status"""
        if self.whisper_model is not None:
            self.model_status_label.config(text="✅ Whisper model ready", fg='#10b981')
        else:
            self.root.after(2000, self.check_model_status)  # Check again in 2 seconds
    
    def create_setting_dropdown(self, parent, label_text, setting_key, options):
        """Create a dropdown setting widget"""
        frame = tk.Frame(parent, bg='white')
        frame.pack(fill='x', padx=20, pady=5)
        
        label = tk.Label(frame, text=label_text, bg='white', font=("Arial", 10))
        label.pack(anchor='w')
        
        var = tk.StringVar(value=self.settings.get(setting_key, options[0]))
        dropdown = ttk.Combobox(frame, textvariable=var, values=options, state='readonly')
        dropdown.pack(fill='x', pady=(2, 0))
        dropdown.bind('<<ComboboxSelected>>', lambda e: self.update_setting(setting_key, var.get()))
        
        setattr(self, f"{setting_key}_var", var)
    
    def create_setting_entry(self, parent, label_text, setting_key, placeholder):
        """Create an entry setting widget"""
        frame = tk.Frame(parent, bg='white')
        frame.pack(fill='x', padx=20, pady=5)
        
        label = tk.Label(frame, text=label_text, bg='white', font=("Arial", 10))
        label.pack(anchor='w')
        
        var = tk.StringVar(value=self.settings.get(setting_key, ''))
        entry = tk.Entry(frame, textvariable=var)
        entry.pack(fill='x', pady=(2, 0))
        entry.bind('<KeyRelease>', lambda e: self.update_setting(setting_key, var.get()))
        
        setattr(self, f"{setting_key}_var", var)
    
    def update_setting(self, key, value):
        """Update a setting and save"""
        self.settings[key] = value
        
        # If Whisper model size changed, reload model
        if key == 'whisper_model_size' and SPEECH_AVAILABLE:
            self.model_status_label.config(text="🔄 Loading new model...", fg='#666')
            self.whisper_model = None
            self.load_whisper_model()
        
        self.save_data()
    
    def create_main_content(self):
        """Create main content area"""
        content_frame = tk.Frame(self.main_container, bg='#f0f0f0')
        content_frame.pack(side='right', fill='both', expand=True)
        
        # Practice section
        practice_card = tk.Frame(content_frame, bg='white', relief='raised', bd=1)
        practice_card.pack(fill='x', pady=(0, 10))
        
        practice_title = tk.Label(
            practice_card,
            text="🔊 AI-Generated Practice Phrase",
            font=("Arial", 16, "bold"),
            bg='white',
            fg='#374151'
        )
        practice_title.pack(pady=(20, 10))
        
        # Phrase display
        self.phrase_text = tk.Text(
            practice_card,
            height=4,
            wrap='word',
            font=("Arial", 14),
            bg='#f8f9fa',
            relief='flat',
            padx=20,
            pady=15
        )
        self.phrase_text.pack(fill='x', padx=20, pady=(0, 10))
        self.phrase_text.insert('1.0', "Click 'Generate AI Phrase' to get started!")
        self.phrase_text.config(state='disabled')
        
        # Context display
        self.context_text = scrolledtext.ScrolledText(
            practice_card,
            height=3,
            wrap='word',
            font=("Arial", 10),
            bg='#fff3e0',
            relief='flat'
        )
        self.context_text.pack(fill='x', padx=20, pady=(0, 15))
        self.context_text.config(state='disabled')
        
        # Control buttons
        button_frame = tk.Frame(practice_card, bg='white')
        button_frame.pack(pady=(0, 20))
        
        self.generate_btn = tk.Button(
            button_frame,
            text="🤖 Generate AI Phrase",
            font=("Arial", 12, "bold"),
            bg='#4f46e5',
            fg='white',
            padx=20,
            pady=10,
            relief='flat',
            cursor='hand2',
            command=self.generate_ai_phrase
        )
        self.generate_btn.pack(side='left', padx=(0, 10))
        
        if SPEECH_AVAILABLE:
            speak_btn = tk.Button(
                button_frame,
                text="🔈 Hear Phrase",
                font=("Arial", 12),
                bg='#06b6d4',
                fg='white',
                padx=20,
                pady=10,
                relief='flat',
                cursor='hand2',
                command=self.speak_phrase
            )
            speak_btn.pack(side='left', padx=(0, 10))
            
            self.record_btn = tk.Button(
                button_frame,
                text="🎙️ Record & Analyze",
                font=("Arial", 12, "bold"),
                bg='#10b981',
                fg='white',
                padx=20,
                pady=10,
                relief='flat',
                cursor='hand2',
                command=self.toggle_recording
            )
            self.record_btn.pack(side='left')
        
        # Results section
        self.results_card = tk.Frame(content_frame, bg='white', relief='raised', bd=1)
        self.results_card.pack(fill='both', expand=True)
        
        results_title = tk.Label(
            self.results_card,
            text="📋 AI Analysis Results (Powered by Whisper)",
            font=("Arial", 16, "bold"),
            bg='white',
            fg='#374151'
        )
        results_title.pack(pady=(20, 10))
        
        # Create results content
        self.create_results_content()
    
    def create_results_content(self):
        """Create results display area"""
        results_container = tk.Frame(self.results_card, bg='white')
        results_container.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        # Left side - transcription and analysis
        left_frame = tk.Frame(results_container, bg='white')
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Transcription
        trans_label = tk.Label(left_frame, text="🧠 Whisper heard:", font=("Arial", 12, "bold"), bg='white')
        trans_label.pack(anchor='w', pady=(10, 5))
        
        self.transcription_text = scrolledtext.ScrolledText(
            left_frame, height=3, wrap='word', bg='#e8f5e8'
        )
        self.transcription_text.pack(fill='x', pady=(0, 10))
        self.transcription_text.config(state='disabled')
        
        # AI Analysis
        analysis_label = tk.Label(left_frame, text="🤖 AI Analysis:", font=("Arial", 12, "bold"), bg='white')
        analysis_label.pack(anchor='w', pady=(10, 5))
        
        self.analysis_text = scrolledtext.ScrolledText(
            left_frame, height=6, wrap='word', bg='#fff3e0'
        )
        self.analysis_text.pack(fill='both', expand=True)
        self.analysis_text.config(state='disabled')
        
        # Right side - score and progress
        right_frame = tk.Frame(results_container, bg='white', width=250)
        right_frame.pack(side='right', fill='y')
        right_frame.pack_propagate(False)
        
        # Score display
        score_label = tk.Label(right_frame, text="Score", font=("Arial", 12, "bold"), bg='white')
        score_label.pack(pady=(10, 5))
        
        self.score_var = tk.StringVar(value="0%")
        score_display = tk.Label(
            right_frame, 
            textvariable=self.score_var,
            font=("Arial", 24, "bold"),
            fg='#4f46e5',
            bg='white'
        )
        score_display.pack(pady=10)
        
        # Progress chart
        self.create_progress_chart(right_frame)
    
    def create_progress_chart(self, parent):
        """Create progress tracking chart"""
        chart_label = tk.Label(parent, text="📈 Progress", font=("Arial", 12, "bold"), bg='white')
        chart_label.pack(pady=(20, 5))
        
        # Create matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(3, 2))
        self.fig.patch.set_facecolor('white')
        self.ax.set_facecolor('white')
        
        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, pady=10)
        
        self.update_progress_chart()
    
    def update_progress_chart(self):
        """Update the progress chart"""
        self.ax.clear()
        
        if len(self.user_data['scores']) > 0:
            sessions = list(range(1, len(self.user_data['scores']) + 1))
            scores = self.user_data['scores']
            
            self.ax.plot(sessions, scores, marker='o', linewidth=2, markersize=4, color='#4f46e5')
            self.ax.set_xlabel('Session')
            self.ax.set_ylabel('Score %')
            self.ax.set_title('Your Progress')
            self.ax.grid(True, alpha=0.3)
            self.ax.set_ylim(0, 100)
        else:
            self.ax.text(0.5, 0.5, 'No data yet\nStart practicing!', 
                        ha='center', va='center', transform=self.ax.transAxes)
            self.ax.set_xlim(0, 1)
            self.ax.set_ylim(0, 1)
        
        self.fig.tight_layout()
        self.canvas.draw()
    
    def update_stats(self):
        """Update quick stats in sidebar"""
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        stats = [
            ("Total Sessions", str(self.user_data['total_sessions'])),
            ("Best Score", f"{self.user_data['best_score']}%"),
            ("Avg Score", f"{self.calculate_avg_score():.1f}%")
        ]
        
        for label, value in stats:
            frame = tk.Frame(self.stats_frame, bg='#f8f9fa', relief='raised', bd=1)
            frame.pack(fill='x', pady=2)
            
            tk.Label(frame, text=value, font=("Arial", 14, "bold"), bg='#f8f9fa', fg='#4f46e5').pack()
            tk.Label(frame, text=label, font=("Arial", 9), bg='#f8f9fa', fg='#666').pack()
    
    def calculate_avg_score(self):
        """Calculate average score"""
        if not self.user_data['scores']:
            return 0.0
        return sum(self.user_data['scores']) / len(self.user_data['scores'])
    
    def generate_ai_phrase(self):
        """Generate AI-powered practice phrase"""
        self.generate_btn.config(state='disabled', text="🤖 Generating...")
        
        # Run in separate thread to avoid freezing UI
        thread = threading.Thread(target=self._generate_phrase_thread)
        thread.daemon = True
        thread.start()
    
    def _generate_phrase_thread(self):
        """Generate phrase in separate thread"""
        try:
            phrase_data = self.call_ai_api_for_phrase()
            
            # Update UI in main thread
            self.root.after(0, lambda: self.update_phrase_ui(phrase_data))
            
        except Exception as e:
            print(f"Error generating phrase: {e}")
            # Fallback phrases
            fallback_phrases = [
                ("The quick brown fox jumps over the lazy dog.", "Classic pangram for practicing all letters."),
                ("She sells seashells by the seashore.", "Great for practicing 'sh' and 's' sounds."),
                ("Peter Piper picked a peck of pickled peppers.", "Excellent alliteration practice.")
            ]
            
            phrase, context = random.choice(fallback_phrases)
            phrase_data = {"phrase": phrase, "explanation": context}
            self.root.after(0, lambda: self.update_phrase_ui(phrase_data))
    
    def call_ai_api_for_phrase(self) -> Dict:
        """Call AI API to generate practice phrase"""
        focus_areas = {
            'general': "balanced practice with common words",
            'pronunciation': "challenging consonant and vowel combinations", 
            'articulation': "clear enunciation of difficult sounds",
            'fluency': "smooth flowing sentences with natural rhythm",
            'consonants': "emphasis on consonant clarity",
            'vowels': "vowel sound differentiation",
            'tongue_twisters': "alliterative phrases for agility"
        }
        
        sample_phrases = {
            'general': [
                "The bright morning sun shines through the window.",
                "Children laughed as they played in the garden.",
                "Technology helps us connect with people worldwide."
            ],
            'pronunciation': [
                "Thirty-three thousand feathers fell from fifty birds.",
                "The sixth sick sheik's sixth sheep's sick.",
                "How much wood would a woodchuck chuck if a woodchuck could chuck wood?"
            ],
            'articulation': [
                "Red leather, yellow leather, red leather, yellow leather.",
                "Unique New York, unique New York, you know you need unique New York.",
                "The lips, the teeth, the tip of the tongue."
            ],
            'fluency': [
                "The rain in Spain stays mainly in the plain, creating beautiful patterns across the landscape.",
                "A successful speech requires proper breathing, clear articulation, and confident delivery.",
                "Modern communication technology bridges distances but cannot replace personal connections."
            ],
            'consonants': [
                "Betty bought some butter but the butter was bitter, so Betty bought some better butter.",
                "Six thick thistle sticks stood still in the thick mist.",
                "The quick brown fox jumps over the lazy dog's back."
            ],
            'vowels': [
                "How now brown cow, eating grass beneath the bough.",
                "The owl hooted through the cool blue moon above the zoo.",
                "Each peach piece teaches speech through reach and beat."
            ],
            'tongue_twisters': [
                "Sally sells seashells by the seashore, surely she shall see some shells soon.",
                "Rubber baby buggy bumpers bounce brightly by the bay.",
                "Fuzzy wuzzy was a bear, fuzzy wuzzy had no hair, fuzzy wuzzy wasn't fuzzy, was he?"
            ]
        }
        
        focus = self.settings['focus_area']
        phrases = sample_phrases.get(focus, sample_phrases['general'])
        
        # Filter by phrase length if needed
        if self.settings['phrase_length'] == 'short':
            phrases = [p for p in phrases if len(p.split()) < 8]
        elif self.settings['phrase_length'] == 'long':
            phrases = [p for p in phrases if len(p.split()) > 12]
        
        if not phrases:  # Fallback if no phrases match criteria
            phrases = sample_phrases['general']
        
        selected_phrase = random.choice(phrases)
        
        # Add topic interest if specified
        topic_interest = self.settings.get('topic_interest', '').strip()
        if topic_interest:
            topic_phrases = {
                'animals': [
                    "The playful dolphins dance through the sparkling ocean waves.",
                    "Majestic elephants trumpeted loudly across the African savanna.",
                    "Colorful butterflies flutter gracefully among the blooming flowers."
                ],
                'technology': [
                    "Artificial intelligence transforms how we process information daily.",
                    "Smartphones connect people instantly across vast global distances.",
                    "Virtual reality creates immersive experiences beyond imagination."
                ],
                'sports': [
                    "Athletes train rigorously to achieve peak physical performance.",
                    "The basketball bounced rhythmically against the gymnasium floor.",
                    "Swimming strengthens muscles while improving cardiovascular health."
                ]
            }
            
            for topic, topic_phrase_list in topic_phrases.items():
                if topic.lower() in topic_interest.lower():
                    selected_phrase = random.choice(topic_phrase_list)
                    break
        
        explanation = f"This phrase focuses on {focus_areas.get(focus, 'general practice')} at {self.settings['difficulty_level']} level."
        if topic_interest:
            explanation += f" Customized for your interest in {topic_interest}."
        
        return {
            "phrase": selected_phrase,
            "explanation": explanation
        }
    
    def update_phrase_ui(self, phrase_data):
        """Update UI with new phrase"""
        self.current_phrase = phrase_data["phrase"]
        self.current_context = phrase_data["explanation"]
        
        # Update phrase display
        self.phrase_text.config(state='normal')
        self.phrase_text.delete('1.0', 'end')
        self.phrase_text.insert('1.0', self.current_phrase)
        self.phrase_text.config(state='disabled')
        
        # Update context
        self.context_text.config(state='normal')
        self.context_text.delete('1.0', 'end')
        self.context_text.insert('1.0', f"🎯 Why this phrase: {self.current_context}")
        self.context_text.config(state='disabled')
        
        # Re-enable button
        self.generate_btn.config(state='normal', text="🤖 Generate AI Phrase")
    
    def speak_phrase(self):
        """Use text-to-speech to speak the current phrase"""
        if not SPEECH_AVAILABLE or not self.tts_engine:
            messagebox.showwarning("Feature Unavailable", "Speech synthesis not available. Please install pyttsx3.")
            return
            
        if not self.current_phrase:
            messagebox.showwarning("No Phrase", "Please generate a phrase first!")
            return
        
        def speak():
            try:
                self.tts_engine.say(self.current_phrase)
                self.tts_engine.runAndWait()
            except Exception as e:
                print(f"TTS Error: {e}")
        
        thread = threading.Thread(target=speak)
        thread.daemon = True
        thread.start()
    
    def toggle_recording(self):
        """Toggle recording state"""
        if not SPEECH_AVAILABLE:
            messagebox.showwarning("Feature Unavailable", "Speech recognition not available. Please install openai-whisper and pyaudio.")
            return
            
        if not self.whisper_model:
            messagebox.showwarning("Model Loading", "Whisper model is still loading. Please wait a moment.")
            return
            
        if not self.current_phrase:
            messagebox.showwarning("No Phrase", "Please generate a phrase first!")
            return
        
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """Start recording audio"""
        self.is_recording = True
        self.audio_frames = []
        self.record_btn.config(text="⏹️ Stop Recording", bg='#ef4444')
        
        def record():
            try:
                # Initialize audio stream
                stream = self.pyaudio_instance.open(
                    format=self.audio_format,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.chunk
                )
                
                print("Recording started...")
                
                # Record audio while is_recording is True
                while self.is_recording:
                    data = stream.read(self.chunk)
                    self.audio_frames.append(data)
                
                # Stop and close stream
                stream.stop_stream()
                stream.close()
                
                print("Recording finished")
                
                # Process the recording
                if self.audio_frames:
                    self.root.after(0, self.process_recording_with_whisper)
                
            except Exception as e:
                print(f"Recording error: {e}")
                self.root.after(0, lambda: messagebox.showerror("Error", f"Recording error: {str(e)}"))
                self.root.after(0, self.reset_record_button)
        
        thread = threading.Thread(target=record)
        thread.daemon = True
        thread.start()
    
    def stop_recording(self):
        """Stop recording"""
        self.is_recording = False
if __name__ == "__main__":
    root = tk.Tk()
    app = VoiceBuddyAI(root)
    root.mainloop()

