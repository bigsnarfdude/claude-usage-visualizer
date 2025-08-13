#!/usr/bin/env python3
"""
Claude Usage Analyzer - Enhanced One-Command Dashboard Generator
Automatically discovers Claude data, processes analysis, and opens dashboard

Usage:
    python claude-analyzer.py --auto --open
    python claude-analyzer.py --data-dir /path/to/claude --output dashboard.html
    python claude-analyzer.py --help
"""

import json
import os
import sys
import argparse
import webbrowser
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict, Counter
import platform

class ClaudeAnalyzer:
    def __init__(self):
        self.conversations = []
        self.usage_stats = {}
        self.session_data = {}
        self.single_file = None
        
    def find_claude_data_directory(self):
        """Auto-discover Claude data directory based on OS"""
        system = platform.system()
        home = Path.home()
        
        possible_paths = []
        
        if system == "Darwin":  # macOS
            possible_paths = [
                home / "Library" / "Application Support" / "claude" / "usage",
                home / "Library" / "Application Support" / "claude-desktop" / "usage",
                home / "Library" / "Application Support" / "Anthropic" / "Claude" / "usage",
                home / ".claude" / "usage",
            ]
        elif system == "Linux":
            possible_paths = [
                home / ".config" / "claude" / "usage",
                home / ".claude" / "usage",
                home / ".local" / "share" / "claude" / "usage",
            ]
        elif system == "Windows":
            appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
            localappdata = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
            possible_paths = [
                appdata / "claude" / "usage",
                localappdata / "claude" / "usage",
                appdata / "Anthropic" / "Claude" / "usage",
            ]
            
        # Check for common development locations
        possible_paths.extend([
            Path.cwd() / "claude_usage_data",
            home / "Downloads" / "claude_usage_data",
            home / "Desktop" / "claude_usage_data",
        ])
        
        for path in possible_paths:
            if path.exists() and any(path.glob("*.json")):
                print(f"📁 Found Claude data directory: {path}")
                return path
                
        return None
    
    def load_conversation_data(self, data_dir):
        """Load and parse Claude conversation data"""
        print(f"🔍 Scanning for conversation files in {data_dir}")
        
        # Handle single file mode
        if self.single_file:
            if self.single_file.suffix == '.json':
                json_files = [self.single_file]
                jsonl_files = []
            else:  # .jsonl
                json_files = []
                jsonl_files = [self.single_file]
        else:
            json_files = list(Path(data_dir).glob("*.json"))
            jsonl_files = list(Path(data_dir).glob("*.jsonl"))
        
        if not json_files and not jsonl_files:
            print("❌ No JSON/JSONL files found in data directory")
            return
            
        print(f"📚 Found {len(json_files)} JSON files and {len(jsonl_files)} JSONL files")
        
        # Process JSON files
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.process_conversation_file(data, file_path)
            except Exception as e:
                print(f"⚠️  Error processing {file_path.name}: {e}")
                continue
        
        # Process JSONL files
        for file_path in jsonl_files:
            try:
                self.process_jsonl_file(file_path)
            except Exception as e:
                print(f"⚠️  Error processing {file_path.name}: {e}")
                continue
    
    def process_jsonl_file(self, file_path):
        """Process JSONL file with Claude conversation data"""
        conversations_by_session = defaultdict(list)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line.strip())
                    session_id = entry.get('sessionId', f'session_{line_num}')
                    conversations_by_session[session_id].append(entry)
                except json.JSONDecodeError as e:
                    print(f"⚠️  Error parsing line {line_num} in {file_path.name}: {e}")
                    continue
        
        # Process each session as a conversation
        for session_id, entries in conversations_by_session.items():
            self.process_session_entries(entries, session_id, file_path)
    
    def process_session_entries(self, entries, session_id, file_path):
        """Process entries from a single session"""
        conversation = {
            'id': session_id,
            'file_path': str(file_path),
            'messages': [],
            'total_tokens': 0,
            'model': 'unknown',
            'created_at': None,
            'last_activity': None,
            'status': 'completed',
            'project_context': 'unknown'
        }
        
        # Sort entries by timestamp
        entries.sort(key=lambda x: x.get('timestamp', ''))
        
        for entry in entries:
            message_info = {
                'role': entry.get('type', 'unknown'),
                'content': '',
                'timestamp': entry.get('timestamp'),
                'tokens': 0
            }
            
            # Extract message content based on entry type
            if entry.get('type') == 'user':
                message_info['role'] = 'user'
                message_content = entry.get('message', {})
                message_info['content'] = message_content.get('content', '')
                
            elif entry.get('type') == 'assistant':
                message_info['role'] = 'assistant'
                message_data = entry.get('message', {})
                
                # Extract model information
                if message_data.get('model'):
                    conversation['model'] = message_data['model']
                
                # Extract content from assistant message
                content_parts = message_data.get('content', [])
                if isinstance(content_parts, list):
                    text_content = []
                    for part in content_parts:
                        if isinstance(part, dict):
                            if part.get('type') == 'text':
                                text_content.append(part.get('text', ''))
                            elif part.get('type') == 'tool_use':
                                # Include tool use information
                                tool_name = part.get('name', 'unknown_tool')
                                text_content.append(f"[Tool: {tool_name}]")
                    message_info['content'] = '\n'.join(text_content)
                elif isinstance(content_parts, str):
                    message_info['content'] = content_parts
                
                # Extract token usage
                usage = message_data.get('usage', {})
                if usage:
                    input_tokens = usage.get('input_tokens', 0)
                    output_tokens = usage.get('output_tokens', 0)
                    message_info['tokens'] = input_tokens + output_tokens
            
            # Estimate tokens if not provided
            if message_info['tokens'] == 0:
                message_info['tokens'] = self.estimate_tokens(message_info['content'])
            
            conversation['messages'].append(message_info)
            conversation['total_tokens'] += message_info['tokens']
            
            # Update timestamps
            if message_info['timestamp']:
                if not conversation['created_at']:
                    conversation['created_at'] = message_info['timestamp']
                conversation['last_activity'] = message_info['timestamp']
        
        # Determine status and context
        conversation['status'] = self.determine_conversation_status(conversation)
        conversation['project_context'] = self.extract_project_context(conversation)
        
        self.conversations.append(conversation)
    
    def process_conversation_file(self, data, file_path):
        """Process individual conversation file"""
        conversation_id = file_path.stem
        
        # Extract conversation metadata
        conversation = {
            'id': conversation_id,
            'file_path': str(file_path),
            'messages': [],
            'total_tokens': 0,
            'model': 'unknown',
            'created_at': None,
            'last_activity': None,
            'status': 'completed',
            'project_context': 'unknown'
        }
        
        # Process messages
        if isinstance(data, list):
            messages = data
        elif isinstance(data, dict) and 'messages' in data:
            messages = data['messages']
        else:
            messages = [data]
            
        for msg in messages:
            if isinstance(msg, dict):
                # Extract message details
                message_info = {
                    'role': msg.get('role', 'unknown'),
                    'content': msg.get('content', ''),
                    'timestamp': msg.get('timestamp'),
                    'tokens': self.estimate_tokens(msg.get('content', ''))
                }
                
                conversation['messages'].append(message_info)
                conversation['total_tokens'] += message_info['tokens']
                
                # Update model info
                if 'model' in msg:
                    conversation['model'] = msg['model']
                
                # Update timestamps
                if message_info['timestamp']:
                    if not conversation['created_at']:
                        conversation['created_at'] = message_info['timestamp']
                    conversation['last_activity'] = message_info['timestamp']
        
        # Determine conversation status and project context
        conversation['status'] = self.determine_conversation_status(conversation)
        conversation['project_context'] = self.extract_project_context(conversation)
        
        self.conversations.append(conversation)
    
    def estimate_tokens(self, text):
        """Rough token estimation (4 chars per token average)"""
        if not text:
            return 0
        return len(str(text)) // 4
    
    def determine_conversation_status(self, conversation):
        """Determine conversation status based on recent activity"""
        if not conversation['last_activity']:
            return 'unknown'
            
        # Check if conversation ended recently (within last hour)
        try:
            last_time = datetime.fromisoformat(conversation['last_activity'].replace('Z', '+00:00'))
            time_diff = datetime.now(timezone.utc) - last_time
            
            if time_diff.seconds < 300:  # 5 minutes
                return 'active'
            elif time_diff.seconds < 3600:  # 1 hour  
                return 'recent'
            else:
                return 'inactive'
        except:
            return 'unknown'
    
    def extract_project_context(self, conversation):
        """Extract project/topic context from conversation"""
        # Look for code patterns, file mentions, or common project terms
        content_sample = ""
        for msg in conversation['messages'][:3]:  # Check first few messages
            content_sample += str(msg.get('content', ''))[:500]
        
        content_lower = content_sample.lower()
        
        # Project type detection
        if any(term in content_lower for term in ['python', '.py', 'import ', 'def ']):
            return 'python'
        elif any(term in content_lower for term in ['javascript', '.js', 'npm', 'node']):
            return 'javascript'  
        elif any(term in content_lower for term in ['react', 'jsx', 'component']):
            return 'react'
        elif any(term in content_lower for term in ['html', 'css', 'web', 'website']):
            return 'web'
        elif any(term in content_lower for term in ['debug', 'error', 'bug', 'fix']):
            return 'debugging'
        elif any(term in content_lower for term in ['data', 'analysis', 'csv', 'pandas']):
            return 'data'
        else:
            return 'general'
    
    def analyze_usage_patterns(self):
        """Analyze usage patterns and generate statistics"""
        if not self.conversations:
            return
            
        # Basic statistics
        total_conversations = len(self.conversations)
        total_messages = sum(len(conv['messages']) for conv in self.conversations)
        total_tokens = sum(conv['total_tokens'] for conv in self.conversations)
        
        # Model usage
        models = Counter(conv['model'] for conv in self.conversations)
        
        # Project distribution  
        projects = Counter(conv['project_context'] for conv in self.conversations)
        
        # Daily usage patterns
        daily_usage = defaultdict(lambda: {'conversations': 0, 'tokens': 0})
        
        for conv in self.conversations:
            if conv['created_at']:
                try:
                    date = datetime.fromisoformat(conv['created_at'].replace('Z', '+00:00')).date()
                    date_str = date.strftime('%Y-%m-%d')
                    daily_usage[date_str]['conversations'] += 1
                    daily_usage[date_str]['tokens'] += conv['total_tokens']
                except:
                    continue
        
        # Status distribution
        statuses = Counter(conv['status'] for conv in self.conversations)
        
        self.usage_stats = {
            'total_conversations': total_conversations,
            'total_messages': total_messages,  
            'total_tokens': total_tokens,
            'models': dict(models),
            'projects': dict(projects),
            'daily_usage': dict(daily_usage),
            'statuses': dict(statuses),
            'avg_tokens_per_conversation': total_tokens / max(total_conversations, 1),
            'avg_messages_per_conversation': total_messages / max(total_conversations, 1)
        }
    
    def generate_enhanced_html(self, output_file="claude_dashboard.html"):
        """Generate enhanced HTML dashboard"""
        
        # Limit conversations for display (show most recent 50)
        display_conversations = sorted(
            self.conversations, 
            key=lambda x: x.get('last_activity') or '1900-01-01T00:00:00Z', 
            reverse=True
        )[:50]
        
        # Clean up conversation content to avoid JSON issues
        for conv in display_conversations:
            for msg in conv.get('messages', []):
                # Truncate very long messages and clean content
                content = str(msg.get('content', ''))
                if len(content) > 500:
                    content = content[:497] + "..."
                # Remove problematic characters
                content = content.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                msg['content'] = content
        
        # Prepare data for JavaScript with proper escaping
        conversations_json = json.dumps(display_conversations, indent=2, ensure_ascii=False)
        stats_json = json.dumps(self.usage_stats, indent=2, ensure_ascii=False)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Usage Analytics Dashboard</title>
    <script src="./chart.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            color: #1a202c;
            line-height: 1.6;
        }}
        
        .header {{
            background: white;
            border-bottom: 1px solid #e2e8f0;
            padding: 1rem 2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            color: #2d3748;
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }}
        
        .update-time {{
            color: #718096;
            font-size: 0.875rem;
        }}
        
        .metrics-bar {{
            background: #4299e1;
            color: white;
            padding: 1rem 2rem;
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
        }}
        
        .metric {{
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        
        .metric-value {{
            font-size: 1.5rem;
            font-weight: bold;
        }}
        
        .metric-label {{
            font-size: 0.875rem;
            opacity: 0.9;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .dashboard-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }}
        
        .chart-container {{
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .chart-title {{
            font-size: 1.125rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #2d3748;
        }}
        
        .conversations-section {{
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .filter-tabs {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
        }}
        
        .filter-tab {{
            padding: 0.5rem 1rem;
            border: 1px solid #e2e8f0;
            background: #f7fafc;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.875rem;
        }}
        
        .filter-tab.active {{
            background: #4299e1;
            color: white;
            border-color: #4299e1;
        }}
        
        .conversations-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .conversations-table th,
        .conversations-table td {{
            text-align: left;
            padding: 0.75rem;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        .conversations-table th {{
            background: #f7fafc;
            font-weight: 600;
            color: #4a5568;
            font-size: 0.875rem;
        }}
        
        .conversations-table td {{
            font-size: 0.875rem;
        }}
        
        .status-dot {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }}
        
        .status-active {{
            background: #48bb78;
        }}
        
        .status-recent {{
            background: #ed8936;  
        }}
        
        .status-inactive {{
            background: #a0aec0;
        }}
        
        .conversation-id {{
            font-family: monospace;
            color: #4299e1;
        }}
        
        .chart-canvas {{
            max-height: 300px;
        }}
        
        @media (max-width: 768px) {{
            .dashboard-grid {{
                grid-template-columns: 1fr;
            }}
            
            .metrics-bar {{
                flex-direction: column;
                gap: 1rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Claude Usage Analytics Dashboard</h1>
        <div class="update-time">Last updated: {datetime.now().strftime('%m/%d/%Y, %I:%M:%S %p')}</div>
    </div>
    
    <div class="metrics-bar">
        <div class="metric">
            <div class="metric-value">{self.usage_stats.get('total_conversations', 0)}</div>
            <div class="metric-label">conversations</div>
        </div>
        <div class="metric">
            <div class="metric-value">{self.usage_stats.get('total_messages', 0)}</div>
            <div class="metric-label">messages</div>
        </div>
        <div class="metric">
            <div class="metric-value">{self.usage_stats.get('total_tokens', 0):,}</div>
            <div class="metric-label">tokens</div>
        </div>
        <div class="metric">
            <div class="metric-value">{len(self.usage_stats.get('projects', {}))}</div>
            <div class="metric-label">projects</div>
        </div>
        <div class="metric">
            <div class="metric-value">{self.usage_stats.get('avg_tokens_per_conversation', 0):.0f}</div>
            <div class="metric-label">avg tokens/conv</div>
        </div>
    </div>
    
    <div class="container">
        <div class="dashboard-grid">
            <div class="chart-container">
                <div class="chart-title">Token Usage Over Time</div>
                <canvas id="tokenChart" class="chart-canvas"></canvas>
            </div>
            
            <div class="chart-container">
                <div class="chart-title">Project Activity Distribution</div>
                <canvas id="projectChart" class="chart-canvas"></canvas>
            </div>
        </div>
        
        <div class="conversations-section">
            <div class="chart-title">Conversations</div>
            
            <div class="filter-tabs">
                <div class="filter-tab active" data-filter="all">all</div>
                <div class="filter-tab" data-filter="active">active</div>
                <div class="filter-tab" data-filter="recent">recent</div>
                <div class="filter-tab" data-filter="inactive">inactive</div>
            </div>
            
            <div style="overflow-x: auto;">
                <table class="conversations-table">
                    <thead>
                        <tr>
                            <th>Conversation ID</th>
                            <th>Project</th>
                            <th>Model</th>
                            <th>Messages</th>
                            <th>Tokens</th>
                            <th>Last Activity</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody id="conversationsTableBody">
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        // Data from Python with error handling
        let conversations = [];
        let stats = {{}};
        
        try {{
            conversations = {conversations_json};
            stats = {stats_json};
        }} catch (e) {{
            console.error('Error parsing data:', e);
            conversations = [];
            stats = {{}};
        }}
        
        // Initialize charts and table
        document.addEventListener('DOMContentLoaded', function() {{
            try {{
                initializeCharts();
                initializeConversationsTable();
                initializeFilters();
            }} catch (e) {{
                console.error('Error initializing dashboard:', e);
                document.body.innerHTML = '<div style="padding: 20px; color: red;">Dashboard initialization failed: ' + e.message + '</div>';
            }}
        }});
        
        function initializeCharts() {{
            // Token Usage Chart
            const tokenCtx = document.getElementById('tokenChart').getContext('2d');
            const dailyUsage = stats.daily_usage || {{}};
            const dates = Object.keys(dailyUsage).sort();
            const tokenData = dates.map(date => dailyUsage[date].tokens || 0);
            
            new Chart(tokenCtx, {{
                type: 'line',
                data: {{
                    labels: dates,
                    datasets: [{{
                        label: 'Tokens',
                        data: tokenData,
                        borderColor: '#4299e1',
                        backgroundColor: 'rgba(66, 153, 225, 0.1)',
                        fill: true,
                        tension: 0.1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            }});
            
            // Project Distribution Chart
            const projectCtx = document.getElementById('projectChart').getContext('2d');
            const projects = stats.projects || {{}};
            const projectLabels = Object.keys(projects);
            const projectData = Object.values(projects);
            
            new Chart(projectCtx, {{
                type: 'bar',
                data: {{
                    labels: projectLabels,
                    datasets: [{{
                        label: 'Conversations',
                        data: projectData,
                        backgroundColor: [
                            '#4299e1', '#48bb78', '#ed8936', '#9f7aea', 
                            '#38b2ac', '#f56565', '#ec4899', '#10b981'
                        ]
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y'
                }}
            }});
        }}
        
        function initializeConversationsTable() {{
            const tbody = document.getElementById('conversationsTableBody');
            renderConversations('all');
        }}
        
        function renderConversations(filter) {{
            const tbody = document.getElementById('conversationsTableBody');
            tbody.innerHTML = '';
            
            let filteredConversations = conversations;
            if (filter !== 'all') {{
                filteredConversations = conversations.filter(conv => conv.status === filter);
            }}
            
            // Sort by last activity (most recent first)
            filteredConversations.sort((a, b) => {{
                if (!a.last_activity && !b.last_activity) return 0;
                if (!a.last_activity) return 1;
                if (!b.last_activity) return -1;
                return new Date(b.last_activity) - new Date(a.last_activity);
            }});
            
            filteredConversations.forEach(conv => {{
                const row = document.createElement('tr');
                
                const statusClass = `status-${{conv.status || 'inactive'}}`;
                const truncatedId = conv.id.substring(0, 12) + '...';
                const lastActivity = conv.last_activity ? 
                    formatTimeAgo(conv.last_activity) : 'unknown';
                
                row.innerHTML = `
                    <td class="conversation-id">${{truncatedId}}</td>
                    <td>${{conv.project_context || 'unknown'}}</td>
                    <td>${{(conv.model || 'unknown').substring(0, 20)}}...</td>
                    <td>${{conv.messages.length}}</td>
                    <td>${{conv.total_tokens.toLocaleString()}}</td>
                    <td>${{lastActivity}}</td>
                    <td><span class="status-dot ${{statusClass}}"></span>${{conv.status || 'unknown'}}</td>
                `;
                
                tbody.appendChild(row);
            }});
        }}
        
        function formatTimeAgo(timestamp) {{
            try {{
                const date = new Date(timestamp);
                const now = new Date();
                const diffMs = now - date;
                const diffMins = Math.floor(diffMs / 60000);
                
                if (diffMins < 1) return 'now';
                if (diffMins < 60) return `${{diffMins}}m ago`;
                
                const diffHours = Math.floor(diffMins / 60);
                if (diffHours < 24) return `${{diffHours}}h ago`;
                
                const diffDays = Math.floor(diffHours / 24);
                return `${{diffDays}}d ago`;
            }} catch {{
                return 'unknown';
            }}
        }}
        
        function initializeFilters() {{
            const filterTabs = document.querySelectorAll('.filter-tab');
            
            filterTabs.forEach(tab => {{
                tab.addEventListener('click', function() {{
                    // Remove active class from all tabs
                    filterTabs.forEach(t => t.classList.remove('active'));
                    
                    // Add active class to clicked tab
                    this.classList.add('active');
                    
                    // Render conversations with filter
                    const filter = this.dataset.filter;
                    renderConversations(filter);
                }});
            }});
        }}
    </script>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"✅ Enhanced dashboard generated: {output_file}")
        return output_file

def main():
    parser = argparse.ArgumentParser(description='Claude Usage Analyzer - Enhanced Dashboard Generator')
    parser.add_argument('--auto', action='store_true', help='Auto-discover Claude data directory')
    parser.add_argument('--data-dir', type=str, help='Path to Claude usage data directory')
    parser.add_argument('--output', type=str, default='claude_dashboard.html', help='Output HTML file name')
    parser.add_argument('--open', action='store_true', help='Open dashboard in browser after generation')
    
    args = parser.parse_args()
    
    if not args.auto and not args.data_dir:
        print("❌ Please specify either --auto or --data-dir")
        parser.print_help()
        return 1
    
    analyzer = ClaudeAnalyzer()
    
    # Find or use specified data directory/file
    if args.auto:
        data_path = analyzer.find_claude_data_directory()
        if not data_path:
            print("❌ Could not auto-discover Claude data directory")
            print("💡 Try specifying the directory or file manually with --data-dir")
            return 1
    else:
        data_path = Path(args.data_dir)
        if not data_path.exists():
            print(f"❌ Data path not found: {data_path}")
            return 1
        
        # If it's a single file, use its parent directory and process only that file
        if data_path.is_file():
            if data_path.suffix in ['.json', '.jsonl']:
                print(f"📁 Processing single file: {data_path}")
                data_dir = data_path.parent
                analyzer.single_file = data_path
            else:
                print(f"❌ Unsupported file type: {data_path.suffix}")
                return 1
        else:
            data_dir = data_path
            analyzer.single_file = None
    
    print(f"🚀 Starting Claude usage analysis...")
    
    # Load and analyze data
    analyzer.load_conversation_data(data_dir)
    analyzer.analyze_usage_patterns()
    
    # Generate dashboard
    output_file = analyzer.generate_enhanced_html(args.output)
    
    # Open in browser if requested
    if args.open:
        print(f"🌐 Opening dashboard in browser...")
        webbrowser.open(f"file://{os.path.abspath(output_file)}")
    
    print(f"🎉 Analysis complete! Dashboard available at: {output_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())