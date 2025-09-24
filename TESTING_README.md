# 🧪 FPL Chatbot Testing Framework

Comprehensive automated testing suite for the FPL Chatbot using AI-powered response evaluation.

## 📋 Overview

This testing framework evaluates your FPL Chatbot's performance across multiple dimensions:
- **Response Accuracy**: Factual correctness of answers
- **Relevance**: How well answers address the query
- **Usefulness**: Practical value for FPL decision-making
- **Completeness**: Depth and detail of responses

## 🚀 Quick Start

### Prerequisites
```bash
# Install testing dependencies
pip install -r test_requirements.txt

# Ensure your .env file has GROQ_API_KEY
echo "GROQ_API_KEY=your_key_here" > .env
```

### Run Tests
```bash
# Method 1: Auto-start server and run tests
python3 run_tests.py

# Method 2: Manual server control
python3 app.py &  # Start server in background
python3 fpl_chatbot_tester.py  # Run tests
```

## 📊 Test Categories

### 🤖 Conversational (4 tests)
- Capability queries ("What can you do?")
- Feature explanations
- Help requests
- Basic interactions

### 👤 Player Queries (5 tests)
- Price information
- Performance statistics
- Captain recommendations
- Budget transfers
- Ownership rankings

### 🏟️ Team Queries (3 tests)
- Fixture information
- Opponent details
- Schedule lookups

### 📋 Rules & Strategy (4 tests)
- Chip combinations
- Captain rules
- Scoring system
- Special events

### 🔄 Transfers & Squad (3 tests)
- Transfer recommendations
- Squad building
- Differential picks

### ⚠️ Edge Cases (4 tests)
- Non-Premier League players
- Invalid queries
- Error handling
- Outdated information

## 📈 Metrics Tracked

### Response Metrics
- **Success Rate**: Percentage of successful API responses
- **Response Time**: Average time per query
- **Error Rate**: Failed requests percentage

### Quality Metrics
- **Pass Rate**: Percentage of acceptable responses
- **Average Score**: Overall quality rating (1-10)
- **Category Breakdown**: Performance by query type

### AI-Powered Judgment
Each response is evaluated by Groq AI on:
- **Accuracy** (1-10): Factual correctness
- **Relevance** (1-10): Query alignment
- **Usefulness** (1-10): Practical value
- **Completeness** (1-10): Information depth

## 📄 Output Files

### `test_results_[timestamp].json`
Complete test results with:
- Individual test case results
- AI judgments and scores
- Response metadata
- Performance metrics

### `test_summary_[timestamp].txt`
Human-readable summary with:
- Overall statistics
- Category breakdown
- Key recommendations
- Performance insights

## 🎯 Interpreting Results

### Score Ranges
- **9-10**: Excellent response
- **7-8**: Good response with minor issues
- **5-6**: Acceptable but needs improvement
- **3-4**: Poor response quality
- **1-2**: Unacceptable response

### Pass Criteria
- **PASS**: Score ≥ 7, accurate and useful
- **PARTIAL**: Score 5-6, mostly correct but incomplete
- **FAIL**: Score < 5, inaccurate or unhelpful

## 🔧 Customization

### Adding Test Cases
Edit the `TEST_CASES` list in `fpl_chatbot_tester.py`:

```python
{
    "query": "Your test query here",
    "category": "player",  # conversational, player, team, rules, transfers, edge_case
    "expected_type": "recommendation"  # informational, factual, recommendation, explanation
}
```

### Modifying Judgment Criteria
Update the AI prompt in `judge_response_with_groq()` method to adjust evaluation standards.

### Changing AI Model
Modify the model parameter in the Groq client call:
```python
model="llama3-8b-8192"  # or other available models
```

## 📊 Sample Output

```
🤖 FPL Chatbot Testing Framework
==================================================
🚀 Starting FPL Chatbot Testing Suite
📊 Total test cases: 23
🔗 Chatbot URL: http://127.0.0.1:8080
🆔 Session ID: test_session_1694300000
✅ Server is running

📋 Test 1/23
🧪 Testing: What can you do?
   📊 Result: PASS (Score: 9)
   💬 Reason: Comprehensive overview of capabilities...

[... test results ...]

🎯 TESTING COMPLETE
==================================================
📊 Overall Pass Rate: 87.0%
⭐ Average Score: 8.2/10
⚡ Response Rate: 100.0%
✅ Excellent performance!
```

## 🐛 Troubleshooting

### Server Connection Issues
```bash
# Check if server is running
curl http://127.0.0.1:8080/health

# Start server manually
python3 app.py
```

### AI Judgment Errors
- Ensure `GROQ_API_KEY` is set in `.env`
- Check API quota and rate limits
- Verify internet connection

### Import Errors
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r test_requirements.txt
```

## 🎯 Best Practices

1. **Run tests regularly** during development
2. **Review failed tests** to identify improvement areas
3. **Add new test cases** for new features
4. **Monitor trends** in pass rates over time
5. **Use results** to prioritize development efforts

## 📈 Continuous Integration

For CI/CD integration, add to your pipeline:

```yaml
- name: Run FPL Chatbot Tests
  run: |
    python3 run_tests.py
    # Check pass rate threshold
    PASS_RATE=$(grep "Pass Rate" test_summary_*.txt | tail -1 | grep -o "[0-9.]*")
    if (( $(echo "$PASS_RATE < 80" | bc -l) )); then
      echo "Test pass rate too low: $PASS_RATE%"
      exit 1
    fi
```

This testing framework ensures your FPL Chatbot maintains high quality and reliability across all query types and use cases.
