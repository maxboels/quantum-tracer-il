#!/usr/bin/env python3
"""
Episode Data Analyzer and Visualizer
====================================

Analyze and visualize collected episode data for debugging and quality assessment.

Usage:
    python3 episode_analyzer.py --episode-dir ./episodes/episode_20250927_143022
    python3 episode_analyzer.py --episodes-dir ./episodes --summary
"""

import argparse
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path
import cv2

class EpisodeAnalyzer:
    """Analyze episode data quality and statistics"""
    
    def __init__(self, episode_dir: str):
        self.episode_dir = Path(episode_dir)
        self.episode_data = None
        self.control_df = None
        self.frame_df = None
        
        self._load_data()
    
    def _load_data(self):
        """Load episode data from JSON and CSV files"""
        
        # Load episode metadata
        metadata_file = self.episode_dir / "episode_data.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                self.episode_data = json.load(f)
        
        # Load control data
        control_csv = self.episode_dir / "control_data.csv"
        if control_csv.exists():
            self.control_df = pd.read_csv(control_csv)
            self.control_df['relative_time'] = self.control_df['system_timestamp'] - self.control_df['system_timestamp'].iloc[0]
        
        # Load frame data
        frame_csv = self.episode_dir / "frame_data.csv"
        if frame_csv.exists():
            self.frame_df = pd.read_csv(frame_csv)
            self.frame_df['relative_time'] = self.frame_df['timestamp'] - self.frame_df['timestamp'].iloc[0]
    
    def print_summary(self):
        """Print episode summary statistics"""
        if not self.episode_data:
            print("No episode data loaded")
            return
            
        print(f"\n📊 Episode Summary: {self.episode_data['episode_id']}")
        print("=" * 60)
        print(f"Duration: {self.episode_data['duration']:.1f} seconds")
        print(f"Start Time: {pd.to_datetime(self.episode_data['start_time'], unit='s')}")
        
        if self.control_df is not None:
            print(f"\n🎮 Control Data:")
            print(f"  Total Samples: {len(self.control_df)}")
            print(f"  Average Rate: {len(self.control_df) / self.episode_data['duration']:.1f} Hz")
            print(f"  Steering Range: [{self.control_df['steering_normalized'].min():.3f}, {self.control_df['steering_normalized'].max():.3f}]")
            print(f"  Throttle Range: [{self.control_df['throttle_normalized'].min():.3f}, {self.control_df['throttle_normalized'].max():.3f}]")
            
            # Control activity analysis
            steering_active = np.abs(self.control_df['steering_normalized']) > 0.1
            throttle_active = self.control_df['throttle_normalized'] > 0.1
            print(f"  Steering Activity: {steering_active.sum() / len(self.control_df) * 100:.1f}%")
            print(f"  Throttle Activity: {throttle_active.sum() / len(self.control_df) * 100:.1f}%")
        
        if self.frame_df is not None:
            print(f"\n📷 Frame Data:")
            print(f"  Total Frames: {len(self.frame_df)}")
            print(f"  Average FPS: {len(self.frame_df) / self.episode_data['duration']:.1f}")
            
            # Check for missing frames
            expected_frames = int(self.episode_data['duration'] * 30)  # Assuming 30 FPS target
            frame_completeness = len(self.frame_df) / expected_frames * 100
            print(f"  Frame Completeness: {frame_completeness:.1f}% ({len(self.frame_df)}/{expected_frames})")
    
    def plot_control_signals(self, save_path: str = None):
        """Plot control signals over time"""
        if self.control_df is None:
            print("No control data available")
            return
            
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        fig.suptitle(f'Control Signals - {self.episode_data["episode_id"]}')
        
        # Steering
        ax1.plot(self.control_df['relative_time'], self.control_df['steering_normalized'], 
                'b-', linewidth=1, alpha=0.7)
        ax1.set_ylabel('Steering\n(Normalized)')
        ax1.set_ylim(-1.1, 1.1)
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=0, color='k', linestyle='--', alpha=0.5)
        
        # Add steering activity regions
        steering_active = np.abs(self.control_df['steering_normalized']) > 0.1
        if steering_active.any():
            ax1.fill_between(self.control_df['relative_time'], -1.1, 1.1, 
                           where=steering_active, alpha=0.2, color='blue', label='Active')
        
        # Throttle
        ax2.plot(self.control_df['relative_time'], self.control_df['throttle_normalized'], 
                'r-', linewidth=1, alpha=0.7)
        ax2.set_ylabel('Throttle\n(Normalized)')
        ax2.set_xlabel('Time (seconds)')
        ax2.set_ylim(-0.1, 1.1)
        ax2.grid(True, alpha=0.3)
        
        # Add throttle activity regions
        throttle_active = self.control_df['throttle_normalized'] > 0.1
        if throttle_active.any():
            ax2.fill_between(self.control_df['relative_time'], -0.1, 1.1, 
                           where=throttle_active, alpha=0.2, color='red', label='Active')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Control plot saved to: {save_path}")
        else:
            plt.show()
    
    def plot_data_rates(self, save_path: str = None):
        """Plot data acquisition rates over time"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6))
        fig.suptitle(f'Data Acquisition Rates - {self.episode_data["episode_id"]}')
        
        # Control data rate
        if self.control_df is not None:
            # Calculate instantaneous rate (samples per second in 1-second windows)
            window_size = 1.0  # 1 second windows
            time_windows = np.arange(0, self.control_df['relative_time'].max(), window_size)
            control_rates = []
            
            for i, t in enumerate(time_windows[:-1]):
                mask = (self.control_df['relative_time'] >= t) & (self.control_df['relative_time'] < t + window_size)
                rate = mask.sum() / window_size
                control_rates.append(rate)
            
            ax1.plot(time_windows[:-1] + window_size/2, control_rates, 'b-', linewidth=2)
            ax1.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='Target: 30 Hz')
            ax1.set_ylabel('Control Rate (Hz)')
            ax1.set_title('Control Data Rate')
            ax1.grid(True, alpha=0.3)
            ax1.legend()
        
        # Frame data rate
        if self.frame_df is not None:
            # Calculate instantaneous frame rate
            window_size = 1.0
            time_windows = np.arange(0, self.frame_df['relative_time'].max(), window_size)
            frame_rates = []
            
            for i, t in enumerate(time_windows[:-1]):
                mask = (self.frame_df['relative_time'] >= t) & (self.frame_df['relative_time'] < t + window_size)
                rate = mask.sum() / window_size
                frame_rates.append(rate)
            
            ax2.plot(time_windows[:-1] + window_size/2, frame_rates, 'r-', linewidth=2)
            ax2.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='Target: 30 FPS')
            ax2.set_ylabel('Frame Rate (FPS)')
            ax2.set_xlabel('Time (seconds)')
            ax2.set_title('Frame Capture Rate')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Rate plot saved to: {save_path}")
        else:
            plt.show()
    
    def create_video_preview(self, output_path: str = None, max_frames: int = 300):
        """Create a video preview of the episode"""
        if self.frame_df is None or len(self.frame_df) == 0:
            print("No frame data available")
            return
        
        if output_path is None:
            output_path = self.episode_dir / "preview.mp4"
        
        # Get first frame to determine dimensions
        first_frame_path = self.episode_dir / self.frame_df.iloc[0]['image_path']
        if not first_frame_path.exists():
            print(f"First frame not found: {first_frame_path}")
            return
        
        first_frame = cv2.imread(str(first_frame_path))
        height, width, _ = first_frame.shape
        
        # Setup video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = min(30, len(self.frame_df) / self.episode_data['duration'])  # Actual or target FPS
        video_writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        # Limit frames for preview
        frames_to_process = min(len(self.frame_df), max_frames)
        step = max(1, len(self.frame_df) // frames_to_process)
        
        print(f"Creating video preview: {frames_to_process} frames at {fps:.1f} FPS")
        
        for i in range(0, len(self.frame_df), step):
            if i >= frames_to_process:
                break
                
            frame_path = self.episode_dir / self.frame_df.iloc[i]['image_path']
            if frame_path.exists():
                frame = cv2.imread(str(frame_path))
                
                # Add timestamp overlay
                timestamp = self.frame_df.iloc[i]['timestamp']
                relative_time = timestamp - self.frame_df.iloc[0]['timestamp']
                
                cv2.putText(frame, f"Time: {relative_time:.2f}s", 
                          (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                # Add control data overlay if available
                if self.control_df is not None:
                    # Find closest control sample
                    time_diffs = np.abs(self.control_df['system_timestamp'] - timestamp)
                    closest_idx = time_diffs.idxmin()
                    control_sample = self.control_df.iloc[closest_idx]
                    
                    steering_text = f"Steering: {control_sample['steering_normalized']:.3f}"
                    throttle_text = f"Throttle: {control_sample['throttle_normalized']:.3f}"
                    
                    cv2.putText(frame, steering_text, (10, 70), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    cv2.putText(frame, throttle_text, (10, 100), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                video_writer.write(frame)
        
        video_writer.release()
        print(f"✅ Video preview saved: {output_path}")
    
    def export_training_format(self, output_path: str = None):
        """Export data in format suitable for training"""
        if output_path is None:
            output_path = self.episode_dir / "training_data.npz"
        
        # Synchronize control and frame data
        synchronized_data = self._synchronize_data()
        
        if synchronized_data is None:
            print("Failed to synchronize data")
            return
        
        # Save as numpy archive
        np.savez_compressed(
            output_path,
            **synchronized_data
        )
        
        print(f"✅ Training data exported: {output_path}")
        print(f"   Synchronized samples: {len(synchronized_data['timestamps'])}")
    
    def _synchronize_data(self):
        """Synchronize control and frame data by timestamp"""
        if self.control_df is None or self.frame_df is None:
            return None
        
        # Use frame timestamps as reference (they're typically less frequent)
        synchronized_data = {
            'timestamps': [],
            'frame_paths': [],
            'steering': [],
            'throttle': []
        }
        
        for _, frame_row in self.frame_df.iterrows():
            frame_time = frame_row['timestamp']
            
            # Find closest control sample
            time_diffs = np.abs(self.control_df['system_timestamp'] - frame_time)
            closest_idx = time_diffs.idxmin()
            
            # Only include if control sample is within reasonable time window (100ms)
            if time_diffs.iloc[closest_idx] < 0.1:
                control_row = self.control_df.iloc[closest_idx]
                
                synchronized_data['timestamps'].append(frame_time)
                synchronized_data['frame_paths'].append(frame_row['image_path'])
                synchronized_data['steering'].append(control_row['steering_normalized'])
                synchronized_data['throttle'].append(control_row['throttle_normalized'])
        
        # Convert to numpy arrays
        for key in synchronized_data:
            if key != 'frame_paths':
                synchronized_data[key] = np.array(synchronized_data[key])
        
        return synchronized_data

def analyze_multiple_episodes(episodes_dir: str):
    """Analyze multiple episodes and create summary report"""
    episodes_path = Path(episodes_dir)
    episode_dirs = [d for d in episodes_path.iterdir() if d.is_dir() and d.name.startswith('episode_')]
    
    if not episode_dirs:
        print(f"No episodes found in {episodes_dir}")
        return
    
    print(f"\n📊 Multi-Episode Analysis")
    print(f"Episodes Directory: {episodes_dir}")
    print(f"Found {len(episode_dirs)} episodes")
    print("=" * 60)
    
    summary_stats = []
    
    for episode_dir in sorted(episode_dirs):
        try:
            analyzer = EpisodeAnalyzer(episode_dir)
            
            if analyzer.episode_data is None:
                continue
                
            stats = {
                'episode_id': analyzer.episode_data['episode_id'],
                'duration': analyzer.episode_data['duration'],
                'control_samples': len(analyzer.control_df) if analyzer.control_df is not None else 0,
                'frame_samples': len(analyzer.frame_df) if analyzer.frame_df is not None else 0,
                'avg_control_rate': len(analyzer.control_df) / analyzer.episode_data['duration'] if analyzer.control_df is not None else 0,
                'avg_frame_rate': len(analyzer.frame_df) / analyzer.episode_data['duration'] if analyzer.frame_df is not None else 0
            }
            
            if analyzer.control_df is not None:
                stats['steering_std'] = analyzer.control_df['steering_normalized'].std()
                stats['throttle_mean'] = analyzer.control_df['throttle_normalized'].mean()
                stats['activity_score'] = (
                    (np.abs(analyzer.control_df['steering_normalized']) > 0.1).sum() + 
                    (analyzer.control_df['throttle_normalized'] > 0.1).sum()
                ) / (2 * len(analyzer.control_df))
            
            summary_stats.append(stats)
            print(f"✅ {stats['episode_id']}: {stats['duration']:.1f}s, {stats['control_samples']} controls, {stats['frame_samples']} frames")
            
        except Exception as e:
            print(f"❌ Failed to analyze {episode_dir.name}: {e}")
    
    if summary_stats:
        # Create summary DataFrame
        summary_df = pd.DataFrame(summary_stats)
        
        print(f"\n📈 Summary Statistics:")
        print(f"Total Episodes: {len(summary_df)}")
        print(f"Total Duration: {summary_df['duration'].sum():.1f} seconds ({summary_df['duration'].sum()/60:.1f} minutes)")
        print(f"Total Control Samples: {summary_df['control_samples'].sum()}")
        print(f"Total Frame Samples: {summary_df['frame_samples'].sum()}")
        print(f"Average Control Rate: {summary_df['avg_control_rate'].mean():.1f} ± {summary_df['avg_control_rate'].std():.1f} Hz")
        print(f"Average Frame Rate: {summary_df['avg_frame_rate'].mean():.1f} ± {summary_df['avg_frame_rate'].std():.1f} FPS")
        
        # Save summary
        summary_path = episodes_path / "episodes_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        print(f"\n💾 Summary saved to: {summary_path}")

def main():
    parser = argparse.ArgumentParser(description='Episode Data Analyzer')
    parser.add_argument('--episode-dir', type=str, help='Single episode directory to analyze')
    parser.add_argument('--episodes-dir', type=str, help='Directory containing multiple episodes')
    parser.add_argument('--summary', action='store_true', help='Multi-episode summary analysis')
    parser.add_argument('--plots', action='store_true', help='Generate plots')
    parser.add_argument('--video', action='store_true', help='Create video preview')
    parser.add_argument('--export', action='store_true', help='Export training format')
    
    args = parser.parse_args()
    
    if args.episodes_dir and args.summary:
        analyze_multiple_episodes(args.episodes_dir)
        return
    
    if not args.episode_dir:
        print("Please specify --episode-dir for single episode analysis or --episodes-dir --summary for multi-episode analysis")
        return
    
    analyzer = EpisodeAnalyzer(args.episode_dir)
    analyzer.print_summary()
    
    if args.plots:
        analyzer.plot_control_signals()
        analyzer.plot_data_rates()
    
    if args.video:
        analyzer.create_video_preview()
    
    if args.export:
        analyzer.export_training_format()

if __name__ == '__main__':
    main()