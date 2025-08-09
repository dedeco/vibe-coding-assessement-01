#!/usr/bin/env python3

import requests
import json
import sys
from typing import Dict, List, Any
from pathlib import Path
import time

class APIResponseTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        
    def test_query(self, question: str, expected_unique_content: List[str] = None) -> Dict[str, Any]:
        """Test a single query and check for unique responses."""
        try:
            response = requests.post(
                f"{self.base_url}/query",
                json={"question": question},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    "question": question,
                    "success": True,
                    "answer": data.get("answer", ""),
                    "relevant_data": data.get("relevant_data", {}),
                    "suggestions": data.get("suggestions", []),
                    "error": None
                }
                
                # Check for hardcoded responses
                hardcoded_indicators = [
                    "R$ 2,450.30",  # From mock data in claude_client.py
                    "CEMIG",         # Hardcoded vendor
                    "March 2025",    # Hardcoded date
                    "What are the highest expenses?",  # Default suggestion
                    "Show me utility costs",           # Default suggestion
                    "What maintenance expenses do we have?"  # Default suggestion
                ]
                
                hardcoded_found = []
                for indicator in hardcoded_indicators:
                    if indicator in result["answer"] or indicator in str(result["suggestions"]):
                        hardcoded_found.append(indicator)
                
                result["hardcoded_indicators"] = hardcoded_found
                result["is_likely_hardcoded"] = len(hardcoded_found) > 0
                
            else:
                result = {
                    "question": question,
                    "success": False,
                    "answer": "",
                    "relevant_data": {},
                    "suggestions": [],
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "hardcoded_indicators": [],
                    "is_likely_hardcoded": False
                }
                
        except Exception as e:
            result = {
                "question": question,
                "success": False,
                "answer": "",
                "relevant_data": {},
                "suggestions": [],
                "error": str(e),
                "hardcoded_indicators": [],
                "is_likely_hardcoded": False
            }
        
        self.test_results.append(result)
        return result
    
    def run_diverse_tests(self) -> Dict[str, Any]:
        """Run tests with diverse questions to detect hardcoded responses."""
        
        test_questions = [
            # Different expense categories
            "How much was spent on electricity?",
            "What are the water utility costs?", 
            "Show me elevator maintenance expenses",
            "What did we pay for cleaning services?",
            "How much was spent on security?",
            
            # Different time periods
            "What were the expenses in January?",
            "Show me February costs",
            "What was spent last month?",
            "Annual expense summary",
            
            # Different vendors
            "Show payments to SABESP",
            "What did we pay to maintenance companies?",
            "Show me all vendor payments",
            
            # Different question types
            "What is the highest single expense?",
            "Show me the cheapest items",
            "Which category costs the most?",
            "List all expense categories",
            "What is the monthly average?",
            
            # Edge cases
            "Tell me about non-existent vendor XYZ Corp",
            "What expenses were there in year 2030?",
            "Show me negative expenses",
            "What about purple elephant costs?",  # Nonsensical query
        ]
        
        print("Starting API Response Tests...")
        print("=" * 60)
        
        for i, question in enumerate(test_questions, 1):
            print(f"Test {i}/{len(test_questions)}: {question}")
            result = self.test_query(question)
            
            if result["success"]:
                print(f"  ✅ Response received")
                if result["is_likely_hardcoded"]:
                    print(f"  ⚠️  HARDCODED INDICATORS FOUND: {result['hardcoded_indicators']}")
                else:
                    print(f"  ✅ No hardcoded indicators detected")
            else:
                print(f"  ❌ Error: {result['error']}")
            
            print(f"  Answer preview: {result['answer'][:100]}...")
            print()
            
            time.sleep(0.5)  # Be nice to the API
        
        return self.analyze_results()
    
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze test results for patterns indicating hardcoded responses."""
        
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r["success"]])
        hardcoded_responses = len([r for r in self.test_results if r["is_likely_hardcoded"]])
        
        # Check for identical responses to different questions
        answers = [r["answer"] for r in self.test_results if r["success"]]
        unique_answers = len(set(answers))
        
        # Find most common response
        from collections import Counter
        answer_counts = Counter(answers)
        most_common_answer = answer_counts.most_common(1)[0] if answer_counts else ("", 0)
        
        # Check suggestions for diversity
        all_suggestions = []
        for result in self.test_results:
            all_suggestions.extend(result["suggestions"])
        
        unique_suggestions = len(set(all_suggestions))
        suggestion_counts = Counter(all_suggestions)
        
        analysis = {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "hardcoded_responses": hardcoded_responses,
                "unique_answers": unique_answers,
                "answer_diversity_ratio": unique_answers / max(successful_tests, 1),
                "unique_suggestions": unique_suggestions
            },
            "most_common_answer": most_common_answer,
            "most_common_suggestions": suggestion_counts.most_common(5),
            "hardcoded_evidence": [],
            "recommendations": []
        }
        
        # Evidence analysis
        if hardcoded_responses > 0:
            analysis["hardcoded_evidence"].append(
                f"{hardcoded_responses}/{successful_tests} responses contain hardcoded indicators"
            )
        
        if unique_answers < successful_tests * 0.7:  # Less than 70% unique responses
            analysis["hardcoded_evidence"].append(
                f"Low answer diversity: only {unique_answers}/{successful_tests} unique responses"
            )
        
        if most_common_answer[1] > successful_tests * 0.5:  # Same answer appears in >50% of responses
            analysis["hardcoded_evidence"].append(
                f"Same answer appears {most_common_answer[1]} times: '{most_common_answer[0][:100]}...'"
            )
        
        # Recommendations
        if len(analysis["hardcoded_evidence"]) > 0:
            analysis["recommendations"].extend([
                "Populate ChromaDB with diverse test data",
                "Remove hardcoded mock data from claude_client.py",
                "Ensure fallback responses are contextual, not static",
                "Add more variation to default suggestions"
            ])
        else:
            analysis["recommendations"].append("API responses appear to be properly dynamic")
        
        return analysis
    
    def save_results(self, filename: str = "api_test_results.json"):
        """Save detailed test results to file."""
        output = {
            "test_results": self.test_results,
            "analysis": self.analyze_results(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"Results saved to {filename}")
        return output

def check_api_health(base_url: str = "http://localhost:8000") -> bool:
    """Check if API is running and healthy."""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"API Status: {data.get('status', 'unknown')}")
            print(f"Components: {data.get('components', {})}")
            return data.get('status') in ['healthy', 'degraded']
        else:
            print(f"API health check failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"Cannot connect to API: {e}")
        return False

def main():
    print("🔍 API Response Testing Suite")
    print("=" * 60)
    
    # Check if API is running
    if not check_api_health():
        print("❌ API is not accessible. Please start the server first:")
        print("   cd src/web && python app.py")
        sys.exit(1)
    
    print()
    
    # Run tests
    tester = APIResponseTester()
    analysis = tester.run_diverse_tests()
    
    # Print analysis
    print("\n" + "=" * 60)
    print("📊 ANALYSIS RESULTS")
    print("=" * 60)
    
    summary = analysis["summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Successful: {summary['successful_tests']}")
    print(f"Hardcoded Indicators: {summary['hardcoded_responses']}")
    print(f"Unique Answers: {summary['unique_answers']}")
    print(f"Answer Diversity: {summary['answer_diversity_ratio']:.2%}")
    
    if analysis["hardcoded_evidence"]:
        print("\n🚨 HARDCODED RESPONSE EVIDENCE:")
        for evidence in analysis["hardcoded_evidence"]:
            print(f"  • {evidence}")
    
    if analysis["recommendations"]:
        print("\n💡 RECOMMENDATIONS:")
        for rec in analysis["recommendations"]:
            print(f"  • {rec}")
    
    # Save results
    results = tester.save_results()
    
    # Return exit code based on findings
    if len(analysis["hardcoded_evidence"]) > 0:
        print("\n❌ Hardcoded response issues detected!")
        sys.exit(1)
    else:
        print("\n✅ No hardcoded response issues found!")
        sys.exit(0)

if __name__ == "__main__":
    main()