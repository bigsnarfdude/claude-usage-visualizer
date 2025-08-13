# Claude Usage Visualizer

A comprehensive toolkit for analyzing and visualizing Claude conversation data from JSONL files.

## Features

- **Interactive HTML Dashboard** - Visual charts and statistics
- **Command-line Analysis** - Detailed reports and JSON output
- **Sample Data** - Realistic fake data for testing

## Files

- `claude-usage-visualizer.html` - Interactive web dashboard
- `analyze_claude_usage.py` - Command-line analysis tool
- `fake_claude_usage.jsonl` - Sample data for testing
- `claude-code_visualizer.png` - Screenshot of the dashboard

## Quick Start

### Web Dashboard
1. Open `claude-usage-visualizer.html` in your browser
2. Upload your JSONL file or use the sample data
3. View interactive charts and statistics

### Command Line Analysis
```bash
# Make the script executable
chmod +x analyze_claude_usage.py

# Analyze sample data
./analyze_claude_usage.py fake_claude_usage.jsonl

# Get JSON output
./analyze_claude_usage.py fake_claude_usage.jsonl --json
```

## Data Format

Expects JSONL files with Claude conversation data containing:
- `sessionId` - Unique session identifier
- `timestamp` - ISO format timestamp
- `type` - Message type (user/assistant)
- `message.usage` - Token usage statistics
- `message.model` - Model name used

## Visualization Features

### Dashboard Charts
- **Timeline**: Messages over time
- **Token Distribution**: Usage histograms
- **Session Analysis**: User vs assistant breakdown
- **Statistics**: Key metrics and totals

### CLI Analysis
- Session patterns and durations
- Token usage breakdown
- Model usage statistics
- Hourly and daily activity patterns

## Requirements

- Modern web browser (for dashboard)
- Python 3.6+ (for CLI tool)
- No additional dependencies required

## License

MIT License - Feel free to use and modify!