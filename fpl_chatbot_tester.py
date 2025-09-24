#!/usr/bin/env python3
"""
FPL Chatbot Testing Framework - SDLC Testing Stage
Automated testing suite to evaluate chatbot responses using AI-powered judgment
"""

import requests
import json
import os
import time
from typing import Dict, List, Any
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
CHATBOT_BASE_URL = "http://127.0.0.1:8080"  # Local development server
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class FPLChatbotTester:
    """Comprehensive testing framework for FPL Chatbot"""

    def __init__(self):
        self.base_url = CHATBOT_BASE_URL
        self.test_results = []
        self.session_id = f"test_session_{int(time.time())}"

    def is_server_running(self) -> bool:
        """Check if the chatbot server is running"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    def ask_chatbot(self, query: str) -> Dict[str, Any]:
        """Send a query to the chatbot and return the response"""
        try:
            payload = {
                "question": query,
                "session_id": self.session_id,
                "quick_mode": True
            }

            response = requests.post(
                f"{self.base_url}/ask",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "response": response.json().get("answer", ""),
                    "status_code": response.status_code
                }
            else:
                return {
                    "success": False,
                    "response": f"HTTP {response.status_code}: {response.text}",
                    "status_code": response.status_code
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "response": "Request timed out after 30 seconds",
                "status_code": None
            }
        except Exception as e:
            return {
                "success": False,
                "response": f"Request failed: {str(e)}",
                "status_code": None
            }

    def judge_response_with_groq(self, query: str, answer: str) -> Dict[str, Any]:
        """Use Groq AI to judge if the chatbot answer is correct/reasonable"""
        # Ensure environment is loaded and check for API key
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            return {
                "verdict": "SKIP",
                "reason": "No GROQ_API_KEY available for AI judgment",
                "score": 0
            }

        try:
            import groq

            client = groq.Groq(api_key=api_key)

            prompt = f"""
            You are an expert Fantasy Premier League analyst evaluating a chatbot response.

            QUERY: {query}
            CHATBOT ANSWER: {answer}

            Evaluate the chatbot's response on these criteria:
            1. Accuracy - Is the information factually correct?
            2. Relevance - Does it directly answer the query?
            3. Usefulness - Is it helpful for FPL decision making?
            4. Completeness - Does it provide sufficient detail?

            Respond in JSON format:
            {{
                "verdict": "PASS" or "FAIL" or "PARTIAL",
                "reason": "Brief explanation of your judgment",
                "score": 1-10 (10 being perfect),
                "accuracy": 1-10,
                "relevance": 1-10,
                "usefulness": 1-10,
                "completeness": 1-10
            }}

            Be strict but fair. FPL context is important.
            """

            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )

            result_text = completion.choices[0].message.content

            # Clean up markdown code blocks and extract JSON
            result_text = result_text.strip()
            
            # Look for JSON content within the response
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_content = result_text[json_start:json_end]
            else:
                json_content = result_text

            # Try to parse JSON response
            try:
                result = json.loads(json_content)
                return result
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "verdict": "PARTIAL" if "pass" in result_text.lower() else "FAIL",
                    "reason": result_text[:200] + "...",
                    "score": 5
                }

        except Exception as e:
            return {
                "verdict": "ERROR",
                "reason": f"AI judgment failed: {str(e)}",
                "score": 0
            }

    def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case"""
        query = test_case["query"]
        category = test_case.get("category", "general")
        expected_type = test_case.get("expected_type", "informational")

        print(f"\n🧪 Testing: {query}")

        # Get chatbot response
        bot_result = self.ask_chatbot(query)

        # Judge the response
        judgment = self.judge_response_with_groq(query, bot_result["response"])

        # Compile test result
        result = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "category": category,
            "expected_type": expected_type,
            "bot_response": bot_result["response"],
            "response_success": bot_result["success"],
            "status_code": bot_result["status_code"],
            "judgment": judgment,
            "overall_verdict": judgment.get("verdict", "UNKNOWN"),
            "score": judgment.get("score", 0)
        }

        print(f"   📊 Result: {result['overall_verdict']} (Score: {result['score']})")
        if judgment.get("reason"):
            print(f"   💬 Reason: {judgment['reason'][:100]}...")

        return result

    def run_test_suite(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run the complete test suite"""
        print("🚀 Starting FPL Chatbot Testing Suite")
        print(f"📊 Total test cases: {len(test_cases)}")
        print(f"🔗 Chatbot URL: {self.base_url}")
        print(f"🆔 Session ID: {self.session_id}")

        # Check server status
        if not self.is_server_running():
            print("❌ Chatbot server is not running!")
            print("💡 Please start the server with: python3 app.py")
            return {"error": "Server not running"}

        print("✅ Server is running")

        # Run all tests
        results = []
        start_time = time.time()

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 Test {i}/{len(test_cases)}")
            result = self.run_single_test(test_case)
            results.append(result)

        end_time = time.time()

        # Generate summary
        summary = self.generate_summary(results, end_time - start_time)

        # Save detailed results
        self.save_results(results, summary)

        return summary

    def generate_summary(self, results: List[Dict[str, Any]], duration: float) -> Dict[str, Any]:
        """Generate a comprehensive test summary"""
        total_tests = len(results)
        successful_responses = sum(1 for r in results if r["response_success"])
        response_rate = (successful_responses / total_tests) * 100

        verdicts = [r["overall_verdict"] for r in results]
        pass_count = verdicts.count("PASS")
        partial_count = verdicts.count("PARTIAL")
        fail_count = verdicts.count("FAIL")
        error_count = verdicts.count("ERROR")
        skip_count = verdicts.count("SKIP")

        scores = [r["score"] for r in results if isinstance(r["score"], (int, float))]
        avg_score = sum(scores) / len(scores) if scores else 0

        # Category breakdown
        categories = {}
        for result in results:
            cat = result["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result["overall_verdict"])

        category_summary = {}
        for cat, verdicts_list in categories.items():
            total = len(verdicts_list)
            passes = verdicts_list.count("PASS")
            category_summary[cat] = {
                "total": total,
                "pass_rate": (passes / total) * 100 if total > 0 else 0
            }

        summary = {
            "test_run_info": {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "total_tests": total_tests,
                "duration_seconds": round(duration, 2),
                "server_url": self.base_url
            },
            "response_metrics": {
                "successful_responses": successful_responses,
                "response_rate_percent": round(response_rate, 2),
                "average_response_time": "N/A"  # Could be added later
            },
            "quality_metrics": {
                "pass_count": pass_count,
                "partial_count": partial_count,
                "fail_count": fail_count,
                "error_count": error_count,
                "skip_count": skip_count,
                "pass_rate_percent": round((pass_count / total_tests) * 100, 2),
                "average_score": round(avg_score, 2)
            },
            "category_breakdown": category_summary
        }

        # Add recommendations after summary is created
        summary["recommendations"] = self.generate_recommendations(summary)

        return summary

    def generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations based on test results"""
        recommendations = []

        pass_rate = summary["quality_metrics"]["pass_rate_percent"]
        response_rate = summary["response_metrics"]["response_rate_percent"]
        avg_score = summary["quality_metrics"]["average_score"]

        if response_rate < 95:
            recommendations.append("Improve server reliability and error handling")

        if pass_rate < 70:
            recommendations.append("Review and improve response accuracy for failed test cases")

        if avg_score < 6:
            recommendations.append("Enhance response quality and completeness")

        if summary["quality_metrics"]["error_count"] > 0:
            recommendations.append("Fix error handling in chatbot responses")

        # Category-specific recommendations
        for cat, stats in summary["category_breakdown"].items():
            if stats["pass_rate"] < 60:
                recommendations.append(f"Improve {cat} query handling")

        if not recommendations:
            recommendations.append("Overall performance is good - consider adding more advanced test cases")

        return recommendations

    def save_results(self, results: List[Dict[str, Any]], summary: Dict[str, Any]):
        """Save test results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save detailed results
        detailed_results = {
            "summary": summary,
            "detailed_results": results
        }

        with open(f"test_results_{timestamp}.json", "w") as f:
            json.dump(detailed_results, f, indent=2)

        # Save summary report
        with open(f"test_summary_{timestamp}.txt", "w") as f:
            f.write("FPL Chatbot Testing Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Test Run: {summary['test_run_info']['timestamp']}\n")
            f.write(f"Session ID: {summary['test_run_info']['session_id']}\n")
            f.write(f"Total Tests: {summary['test_run_info']['total_tests']}\n")
            f.write(f"Duration: {summary['test_run_info']['duration_seconds']} seconds\n\n")

            f.write("RESPONSE METRICS:\n")
            f.write(f"- Success Rate: {summary['response_metrics']['response_rate_percent']}%\n\n")

            f.write("QUALITY METRICS:\n")
            f.write(f"- Pass Rate: {summary['quality_metrics']['pass_rate_percent']}%\n")
            f.write(f"- Average Score: {summary['quality_metrics']['average_score']}/10\n")
            f.write(f"- Pass: {summary['quality_metrics']['pass_count']}\n")
            f.write(f"- Partial: {summary['quality_metrics']['partial_count']}\n")
            f.write(f"- Fail: {summary['quality_metrics']['fail_count']}\n")
            f.write(f"- Error: {summary['quality_metrics']['error_count']}\n\n")

            f.write("CATEGORY BREAKDOWN:\n")
            for cat, stats in summary["category_breakdown"].items():
                f.write(f"- {cat}: {stats['pass_rate']:.1f}% pass rate ({stats['total']} tests)\n")

            f.write("\nRECOMMENDATIONS:\n")
            for rec in summary["recommendations"]:
                f.write(f"- {rec}\n")

        print(f"\n💾 Results saved to:")
        print(f"   📄 test_results_{timestamp}.json")
        print(f"   📄 test_summary_{timestamp}.txt")


# Comprehensive test cases for FPL Chatbot
TEST_CASES = [
    # Conversational queries
    {"query": "What can you do?", "category": "conversational", "expected_type": "capabilities"},
    {"query": "Tell me about your features", "category": "conversational", "expected_type": "capabilities"},
    {"query": "Explain what you do", "category": "conversational", "expected_type": "capabilities"},
    {"query": "Can you help me with FPL?", "category": "conversational", "expected_type": "confirmation"},

    # Player queries
    {"query": "How much does Harry Kane cost?", "category": "player", "expected_type": "price"},
    {"query": "What's Mohamed Salah's form?", "category": "player", "expected_type": "statistics"},
    {"query": "Who should I captain this week?", "category": "player", "expected_type": "recommendation"},
    {"query": "Suggest a cheap midfielder under 6.0M", "category": "player", "expected_type": "recommendation"},
    {"query": "Show me the top 5 most-owned forwards", "category": "player", "expected_type": "ranking"},

    # Team queries
    {"query": "What are Arsenal's next fixtures?", "category": "team", "expected_type": "fixtures"},
    {"query": "When does Manchester United play next?", "category": "team", "expected_type": "fixtures"},
    {"query": "Who is playing against Chelsea in GW5?", "category": "team", "expected_type": "opponent"},

    # Rules and strategy
    {"query": "Can I use Free Hit and Wildcard in the same week?", "category": "rules", "expected_type": "explanation"},
    {"query": "What happens if my captain doesn't play?", "category": "rules", "expected_type": "explanation"},
    {"query": "How many points do I get for an assist?", "category": "rules", "expected_type": "factual"},
    {"query": "Explain the blank gameweek", "category": "rules", "expected_type": "explanation"},

    # Transfer and squad building
    {"query": "Recommend transfers for GW10 if I have Haaland and Salah", "category": "transfers", "expected_type": "recommendation"},
    {"query": "Can you build me a squad within 100M budget?", "category": "squad", "expected_type": "recommendation"},
    {"query": "Suggest a differential defender", "category": "transfers", "expected_type": "recommendation"},

    # Edge cases and error handling
    {"query": "What is Lionel Messi's current form?", "category": "edge_case", "expected_type": "error_handling"},
    {"query": "Tell me about Real Madrid's fixtures", "category": "edge_case", "expected_type": "error_handling"},
    {"query": "", "category": "edge_case", "expected_type": "error_handling"},
    {"query": "Who won the Premier League in 2020?", "category": "edge_case", "expected_type": "error_handling"},
]


def main():
    """Main testing function"""
    print("🤖 FPL Chatbot Testing Framework")
    print("=" * 50)

    # Initialize tester
    tester = FPLChatbotTester()

    # Run the test suite
    summary = tester.run_test_suite(TEST_CASES)

    # Print final summary
    print("\n" + "=" * 50)
    print("🎯 TESTING COMPLETE")
    print("=" * 50)
    print(f"📊 Overall Pass Rate: {summary['quality_metrics']['pass_rate_percent']}%")
    print(f"⭐ Average Score: {summary['quality_metrics']['average_score']}/10")
    print(f"⚡ Response Rate: {summary['response_metrics']['response_rate_percent']}%")

    if summary['quality_metrics']['pass_rate_percent'] >= 80:
        print("✅ Excellent performance!")
    elif summary['quality_metrics']['pass_rate_percent'] >= 60:
        print("🟡 Good performance with room for improvement")
    else:
        print("❌ Needs significant improvements")

    print("\n📋 Key Recommendations:")
    for rec in summary['recommendations'][:3]:  # Show top 3
        print(f"   • {rec}")


if __name__ == "__main__":
    main()
