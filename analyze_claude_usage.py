#!/usr/bin/env python3
"""
Claude Usage Analytics Script
Analyzes JSONL files containing Claude conversation data
"""

import json
import sys
from datetime import datetime
from collections import defaultdict, Counter
import argparse

def load_jsonl(file_path):
    """Load and parse JSONL file"""
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Warning: Skipping invalid JSON on line {line_num}: {e}")
        return data
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def analyze_basic_stats(data):
    """Calculate basic statistics"""
    total_messages = len(data)
    sessions = set(entry.get('sessionId', 'unknown') for entry in data)
    user_types = Counter(entry.get('userType', 'unknown') for entry in data)
    message_types = Counter(entry.get('type', 'unknown') for entry in data)
    
    return {
        'total_messages': total_messages,
        'unique_sessions': len(sessions),
        'user_types': dict(user_types),
        'message_types': dict(message_types)
    }

def analyze_tokens(data):
    """Analyze token usage"""
    token_stats = {
        'total_input_tokens': 0,
        'total_output_tokens': 0,
        'total_cache_tokens': 0,
        'messages_with_usage': 0,
        'token_distribution': []
    }
    
    for entry in data:
        if 'message' in entry and 'usage' in entry['message']:
            usage = entry['message']['usage']
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            cache_tokens = usage.get('cache_creation_input_tokens', 0) + usage.get('cache_read_input_tokens', 0)
            
            token_stats['total_input_tokens'] += input_tokens
            token_stats['total_output_tokens'] += output_tokens
            token_stats['total_cache_tokens'] += cache_tokens
            token_stats['messages_with_usage'] += 1
            
            total_msg_tokens = input_tokens + output_tokens
            if total_msg_tokens > 0:
                token_stats['token_distribution'].append(total_msg_tokens)
    
    if token_stats['token_distribution']:
        tokens = token_stats['token_distribution']
        token_stats['avg_tokens_per_message'] = sum(tokens) / len(tokens)
        token_stats['max_tokens_per_message'] = max(tokens)
        token_stats['min_tokens_per_message'] = min(tokens)
    
    return token_stats

def analyze_timeline(data):
    """Analyze usage over time"""
    daily_counts = defaultdict(int)
    hourly_counts = defaultdict(int)
    
    for entry in data:
        timestamp_str = entry.get('timestamp')
        if timestamp_str:
            try:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                date_key = dt.date().isoformat()
                hour_key = dt.hour
                
                daily_counts[date_key] += 1
                hourly_counts[hour_key] += 1
            except Exception:
                continue
    
    return {
        'daily_usage': dict(daily_counts),
        'hourly_distribution': dict(hourly_counts)
    }

def analyze_models(data):
    """Analyze model usage"""
    model_counts = Counter()
    
    for entry in data:
        if 'message' in entry and 'model' in entry['message']:
            model = entry['message']['model']
            model_counts[model] += 1
    
    return dict(model_counts)

def analyze_sessions(data):
    """Analyze session patterns"""
    session_data = defaultdict(list)
    
    for entry in data:
        session_id = entry.get('sessionId', 'unknown')
        session_data[session_id].append(entry)
    
    session_stats = {
        'total_sessions': len(session_data),
        'messages_per_session': [],
        'session_durations': []
    }
    
    for session_id, messages in session_data.items():
        session_stats['messages_per_session'].append(len(messages))
        
        # Calculate session duration
        timestamps = []
        for msg in messages:
            timestamp_str = msg.get('timestamp')
            if timestamp_str:
                try:
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    timestamps.append(dt)
                except Exception:
                    continue
        
        if len(timestamps) > 1:
            duration_minutes = (max(timestamps) - min(timestamps)).total_seconds() / 60
            session_stats['session_durations'].append(duration_minutes)
    
    if session_stats['messages_per_session']:
        msgs = session_stats['messages_per_session']
        session_stats['avg_messages_per_session'] = sum(msgs) / len(msgs)
    
    if session_stats['session_durations']:
        durations = session_stats['session_durations']
        session_stats['avg_session_duration_minutes'] = sum(durations) / len(durations)
    
    return session_stats

def print_report(analysis):
    """Print formatted analysis report"""
    print("=" * 60)
    print("CLAUDE USAGE ANALYSIS REPORT")
    print("=" * 60)
    
    # Basic Stats
    basic = analysis['basic_stats']
    print(f"\n📊 BASIC STATISTICS")
    print(f"Total Messages: {basic['total_messages']:,}")
    print(f"Unique Sessions: {basic['unique_sessions']:,}")
    print(f"User Types: {basic['user_types']}")
    print(f"Message Types: {basic['message_types']}")
    
    # Token Analysis
    tokens = analysis['token_stats']
    print(f"\n🔢 TOKEN USAGE")
    print(f"Total Input Tokens: {tokens['total_input_tokens']:,}")
    print(f"Total Output Tokens: {tokens['total_output_tokens']:,}")
    print(f"Total Cache Tokens: {tokens['total_cache_tokens']:,}")
    print(f"Messages with Usage Data: {tokens['messages_with_usage']:,}")
    if 'avg_tokens_per_message' in tokens:
        print(f"Average Tokens per Message: {tokens['avg_tokens_per_message']:.1f}")
        print(f"Token Range: {tokens['min_tokens_per_message']:,} - {tokens['max_tokens_per_message']:,}")
    
    # Session Analysis
    sessions = analysis['session_stats']
    print(f"\n💬 SESSION ANALYSIS")
    print(f"Total Sessions: {sessions['total_sessions']:,}")
    if 'avg_messages_per_session' in sessions:
        print(f"Average Messages per Session: {sessions['avg_messages_per_session']:.1f}")
    if 'avg_session_duration_minutes' in sessions:
        print(f"Average Session Duration: {sessions['avg_session_duration_minutes']:.1f} minutes")
    
    # Model Usage
    models = analysis['models']
    if models:
        print(f"\n🤖 MODEL USAGE")
        for model, count in sorted(models.items(), key=lambda x: x[1], reverse=True):
            print(f"  {model}: {count:,} messages")
    
    # Timeline
    timeline = analysis['timeline']
    if timeline['daily_usage']:
        print(f"\n📅 USAGE TIMELINE")
        print(f"Date Range: {min(timeline['daily_usage'].keys())} to {max(timeline['daily_usage'].keys())}")
        print(f"Most Active Day: {max(timeline['daily_usage'].items(), key=lambda x: x[1])}")
        
        if timeline['hourly_distribution']:
            peak_hour = max(timeline['hourly_distribution'].items(), key=lambda x: x[1])
            print(f"Peak Hour: {peak_hour[0]}:00 ({peak_hour[1]} messages)")

def main():
    parser = argparse.ArgumentParser(description='Analyze Claude usage JSONL files')
    parser.add_argument('file', help='Path to JSONL file')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    
    args = parser.parse_args()
    
    # Load data
    data = load_jsonl(args.file)
    if data is None:
        sys.exit(1)
    
    if len(data) == 0:
        print("No valid data found in file")
        sys.exit(1)
    
    # Perform analysis
    analysis = {
        'basic_stats': analyze_basic_stats(data),
        'token_stats': analyze_tokens(data),
        'timeline': analyze_timeline(data),
        'models': analyze_models(data),
        'session_stats': analyze_sessions(data)
    }
    
    # Output results
    if args.json:
        print(json.dumps(analysis, indent=2, default=str))
    else:
        print_report(analysis)

if __name__ == '__main__':
    main()