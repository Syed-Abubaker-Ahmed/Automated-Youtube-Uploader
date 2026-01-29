"""
Prompt Manager & Trend Analyzer
Tracks generated prompts and generates unique ones based on trends
"""

import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

class PromptHistory:
    """Manages history of generated prompts"""
    
    def __init__(self, history_file: str = "data/prompt_history.json"):
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history = self._load_history()
    
    def _load_history(self) -> List[Dict]:
        """Load prompt history from file"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load history: {e}")
                return []
        return []
    
    def save_history(self):
        """Save prompt history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
            logger.info(f"Saved {len(self.history)} prompts to history")
        except Exception as e:
            logger.error(f"Could not save history: {e}")
    
    def add_prompt(self, prompt: str, platform: str = "all") -> bool:
        """Add prompt to history after successful generation"""
        entry = {
            'prompt': prompt,
            'timestamp': datetime.now().isoformat(),
            'platform': platform,
            'status': 'generated'
        }
        self.history.append(entry)
        self.save_history()
        logger.info(f"Added to history: {prompt}")
        return True
    
    def get_used_prompts(self, days: int = 30) -> List[str]:
        """Get prompts used in the last N days"""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        used = []
        for entry in self.history:
            try:
                timestamp = datetime.fromisoformat(entry['timestamp']).timestamp()
                if timestamp > cutoff:
                    used.append(entry['prompt'])
            except:
                pass
        
        return used
    
    def prompt_is_unique(self, prompt: str, days: int = 30) -> bool:
        """Check if prompt hasn't been used recently"""
        used = self.get_used_prompts(days)
        return prompt.lower() not in [p.lower() for p in used]
    
    def get_statistics(self) -> Dict:
        """Get statistics about generated prompts"""
        return {
            'total_generated': len(self.history),
            'last_generated': self.history[-1]['timestamp'] if self.history else None,
            'platforms_used': list(set(e.get('platform', 'unknown') for e in self.history)),
            'unique_prompts': len(set(e['prompt'].lower() for e in self.history))
        }


class TrendBasedPromptGenerator:
    """Generates prompts based on current trends"""
    
    def __init__(self):
        self.history = PromptHistory()
        self.base_prompts = self._get_base_prompts()
        self.trending_topics = self._load_trending_topics()
    
    def _get_base_prompts(self) -> Dict[str, List[str]]:
        """Get template prompts for different styles"""
        return {
            'cute': [
                "A {animal} doing {action}",
                "An adorable {animal} {action}",
                "{animal} being cute while {action}",
                "Cutest {animal} {action}",
            ],
            'funny': [
                "A funny {animal} {action}",
                "{animal} trying to {action}",
                "Hilarious {animal} {action}",
                "Silly {animal} {action}",
            ],
            'active': [
                "An energetic {animal} {action}",
                "{animal} running and {action}",
                "{animal} playing and {action}",
                "Playful {animal} {action}",
            ],
            'relaxing': [
                "A peaceful {animal} {action}",
                "{animal} relaxing and {action}",
                "Calm {animal} {action}",
            ],
            'nature': [
                "A {animal} in nature {action}",
                "{animal} outdoors {action}",
                "Wild {animal} {action}",
            ]
        }
    
    def _load_trending_topics(self) -> Dict[str, Dict]:
        """Load current trending topics and hashtags"""
        # These are updated based on real platform trends
        # In production, fetch from API
        return {
            'animals': {
                'most_popular': ['golden retriever', 'cat', 'corgi', 'husky', 'persian cat', 'poodle'],
                'trending': ['capybara', 'axolotl', 'ferret', 'bunny', 'hamster'],
            },
            'actions': {
                'cute': ['playing', 'sleeping', 'yawning', 'stretching', 'learning tricks'],
                'funny': ['failing at tricks', 'being jealous', 'reacting to', 'confused about'],
                'active': ['running', 'jumping', 'fetching', 'playing fetch', 'swimming'],
                'relaxing': ['napping', 'grooming', 'watching', 'lounging', 'meditating'],
                'nature': ['exploring', 'running wild', 'hunting', 'adventuring', 'discovering']
            },
            'locations': [
                'in a sunny park',
                'at the beach',
                'in the snow',
                'in autumn leaves',
                'at a dog spa',
                'at home',
                'in the backyard',
                'at the dog park',
                'in the garden',
                'by a lake'
            ]
        }
    
    def generate_unique_prompt(self, style: str = None) -> str:
        """Generate a unique prompt based on trends"""
        max_attempts = 10
        
        for attempt in range(max_attempts):
            prompt = self._create_prompt(style)
            
            if self.history.prompt_is_unique(prompt, days=30):
                logger.info(f"Generated unique prompt: {prompt}")
                return prompt
            
            logger.debug(f"Prompt already used, trying again (attempt {attempt+1}/{max_attempts})")
        
        logger.warning(f"Could not generate unique prompt after {max_attempts} attempts")
        return self._create_prompt(style)
    
    def _create_prompt(self, style: str = None) -> str:
        """Create a prompt from trends"""
        if style is None:
            style = random.choice(list(self.base_prompts.keys()))
        
        trends = self.trending_topics
        template = random.choice(self.base_prompts[style])
        
        # Choose animal (mix of popular and trending)
        if random.random() < 0.7:  # 70% popular
            animal = random.choice(trends['animals']['most_popular'])
        else:  # 30% trending
            animal = random.choice(trends['animals']['trending'])
        
        # Choose action based on style
        action = random.choice(trends['actions'].get(style, trends['actions']['cute']))
        
        # Add location sometimes
        if random.random() < 0.6:
            location = random.choice(trends['locations'])
            template += f" {location}"
        
        # Create prompt
        prompt = template.format(animal=animal, action=action)
        
        return prompt
    
    def update_trends(self, new_trends: Dict = None):
        """Update trending topics from platform analytics"""
        if new_trends:
            # Merge new trends with existing
            for key, value in new_trends.items():
                if key in self.trending_topics:
                    self.trending_topics[key].update(value)
                else:
                    self.trending_topics[key] = value
            
            logger.info("Trends updated")
    
    def get_trending_animals(self) -> List[str]:
        """Get currently trending animals"""
        return (self.trending_topics['animals']['most_popular'] + 
                self.trending_topics['animals']['trending'])
    
    def get_popular_actions(self, style: str = None) -> List[str]:
        """Get popular actions for a style"""
        if style:
            return self.trending_topics['actions'].get(style, [])
        else:
            all_actions = []
            for actions in self.trending_topics['actions'].values():
                all_actions.extend(actions)
            return all_actions


class AnalyticsFetcher:
    """Fetch real trending data from platforms"""
    
    @staticmethod
    def fetch_youtube_trends() -> Dict:
        """Fetch trending topics from YouTube"""
        # In production, use YouTube Trends API or scraping
        logger.info("Would fetch YouTube trends here")
        return {}
    
    @staticmethod
    def fetch_tiktok_trends() -> Dict:
        """Fetch trending topics from TikTok"""
        # In production, use TikTok API trends endpoint
        logger.info("Would fetch TikTok trends here")
        return {}
    
    @staticmethod
    def fetch_instagram_trends() -> Dict:
        """Fetch trending topics from Instagram"""
        # In production, use Instagram API or hashtag analytics
        logger.info("Would fetch Instagram trends here")
        return {}
    
    @classmethod
    def fetch_all_trends(cls) -> Dict:
        """Fetch trends from all platforms"""
        return {
            'youtube': cls.fetch_youtube_trends(),
            'tiktok': cls.fetch_tiktok_trends(),
            'instagram': cls.fetch_instagram_trends(),
        }


class SmartPromptManager:
    """Main manager combining history and trend-based generation"""
    
    def __init__(self):
        self.generator = TrendBasedPromptGenerator()
        self.history = self.generator.history
        self.analytics = AnalyticsFetcher()
    
    def get_next_prompt(self, refresh_trends: bool = False) -> str:
        """
        Get the next prompt to generate
        
        Args:
            refresh_trends: If True, fetch fresh trends from platforms
        
        Returns:
            Unique prompt based on current trends
        """
        if refresh_trends:
            self._update_trends()
        
        prompt = self.generator.generate_unique_prompt()
        return prompt
    
    def save_generated_prompt(self, prompt: str, platform: str = "all"):
        """Save prompt after successful generation"""
        self.history.add_prompt(prompt, platform)
    
    def _update_trends(self):
        """Fetch and update trends from platforms"""
        try:
            trends = self.analytics.fetch_all_trends()
            if trends:
                self.generator.update_trends(trends)
                logger.info("Trends updated from platforms")
        except Exception as e:
            logger.warning(f"Could not update trends: {e}")
    
    def get_status(self) -> Dict:
        """Get current status and statistics"""
        stats = self.history.get_statistics()
        return {
            'statistics': stats,
            'trending_animals': self.generator.get_trending_animals(),
            'next_style': random.choice(list(self.generator.base_prompts.keys())),
            'history_file': str(self.history.history_file)
        }
    
    def view_history(self, limit: int = 10) -> List[Dict]:
        """View recent prompt history"""
        return self.history.history[-limit:]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    manager = SmartPromptManager()
    
    # Get next prompt
    prompt = manager.get_next_prompt(refresh_trends=False)
    print(f"Next prompt: {prompt}")
    
    # View status
    status = manager.get_status()
    print(f"\nStatus: {json.dumps(status, indent=2)}")
    
    # View recent history
    print(f"\nRecent prompts:")
    for entry in manager.view_history(5):
        print(f"  - {entry['prompt']}")
