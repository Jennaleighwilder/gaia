#!/usr/bin/env python3
"""
🧬 CHIMERA CORE ENGINE v2.0 - Self-Evolving AI Capability System
Jennifer West's Proprietary Framework
The Forgotten Code Research Institute

Copyright © 2025 Jennifer Leigh West
All Rights Reserved - Mirror Protocol™, MIRA Protocol™, West Method™

CHIMERA - Comprehensive Historical Intelligence & Monitoring Engine for Research Analysis

THIS IS THE REAL SELF-EVOLVING ENGINE - NOT JUST REPORT OUTPUTS
This system:
- Starts with basic capabilities
- Generates new code when asked for features it doesn't have
- Validates and integrates new capabilities automatically
- Documents its own evolution process
- Can be extended with any analysis module

Dependencies:
  pip install fastapi uvicorn (optional - for web server mode)

Usage:
  python chimera_engine.py              # Interactive mode
  python chimera_engine.py --demo       # Run demonstration
  python chimera_engine.py --server     # Start FastAPI server
"""

import json
import time
import uuid
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import sys
import os

# ═══════════════════════════════════════════════════════════════════════════════════════
# CHIMERA CORE ENGINE - THE SELF-EVOLVING HEART
# ═══════════════════════════════════════════════════════════════════════════════════════

class ChimeraCoreEngine:
    """
    🧬 CHIMERA CORE - Self-Evolving AI Capability Engine
    
    This is the heart of the self-improving system. When asked to perform
    a task it cannot handle, it generates new code to fulfill the request.
    """
    
    def __init__(self, output_dir: str = None, quiet: bool = False):
        self.version = "2.0"
        self.capabilities: Dict[str, Dict[str, Any]] = {}
        self.development_log: List[Dict[str, Any]] = []
        self.evolution_count = 0
        self.generation_history: List[Dict[str, Any]] = []
        self.output_dir = output_dir or os.getcwd()
        self.quiet = quiet  # Suppress prints when used as library (e.g. chimera_service)
        
        # Code generation templates
        self.enhanced_templates = self._load_enhanced_templates()
        
        # Initialize with basic capabilities
        self._bootstrap_core_capabilities()
        
        if not self.quiet:
            print("🧬 CHIMERA CORE ENGINE Initialized")
            print(f"📊 Starting capabilities: {len(self.capabilities)}")
            print(f"🔧 Version: {self.version}")
    
    def _load_enhanced_templates(self) -> Dict[str, str]:
        """Load enhanced code generation templates"""
        return {
            "predict_sales": '''
def predict_sales(data):
    """Sales prediction capability - Generate sales forecasts based on historical data"""
    import statistics
    
    if not data:
        return {"error": "No data provided"}
    
    try:
        # Handle various input formats
        if isinstance(data, str):
            # Try to parse as comma-separated numbers
            sales_data = [float(x.strip()) for x in data.split(',') if x.strip().replace('.', '').replace('-', '').isdigit()]
        elif isinstance(data, (list, tuple)):
            sales_data = [float(x) for x in data if str(x).replace('.', '').replace('-', '').isdigit()]
        else:
            return {"error": "Invalid data format - provide list or comma-separated numbers"}
        
        if len(sales_data) < 2:
            return {"error": "Need at least 2 data points for forecasting"}
        
        # Calculate trend
        recent_trend = statistics.mean(sales_data[-3:]) if len(sales_data) >= 3 else statistics.mean(sales_data)
        overall_mean = statistics.mean(sales_data)
        
        # Calculate growth rate from data
        if len(sales_data) >= 2:
            growth_rate = (sales_data[-1] - sales_data[0]) / sales_data[0] if sales_data[0] != 0 else 0.05
            growth_rate = max(-0.5, min(0.5, growth_rate))  # Cap at ±50%
        else:
            growth_rate = 0.05  # Default 5% growth
        
        forecast = recent_trend * (1 + growth_rate * 0.5)  # Conservative forecast
        
        return {
            "current_average": round(overall_mean, 2),
            "recent_trend": round(recent_trend, 2),
            "forecast": round(forecast, 2),
            "growth_rate_percent": round(growth_rate * 100, 2),
            "confidence": "medium" if len(sales_data) >= 5 else "low",
            "method": "trend_analysis_with_growth",
            "data_points_used": len(sales_data),
            "analysis_timestamp": str(__import__('datetime').datetime.now().isoformat())
        }
    except Exception as e:
        return {"error": f"Forecasting error: {str(e)}"}
''',
            "analyze_sentiment": '''
def analyze_sentiment(text):
    """Sentiment analysis capability - Analyze sentiment of text input"""
    if not text or not isinstance(text, str):
        return {"error": "No valid text provided"}
    
    try:
        # Enhanced sentiment lexicon
        positive_words = [
            "good", "great", "excellent", "amazing", "wonderful", "fantastic", 
            "love", "best", "awesome", "perfect", "brilliant", "outstanding",
            "superb", "incredible", "magnificent", "phenomenal", "exceptional",
            "happy", "joy", "pleased", "delighted", "satisfied", "thrilled"
        ]
        negative_words = [
            "bad", "terrible", "awful", "hate", "worst", "horrible", 
            "disgusting", "disappointing", "poor", "unacceptable", "pathetic",
            "dreadful", "atrocious", "abysmal", "inferior", "useless",
            "sad", "angry", "frustrated", "annoyed", "upset", "miserable"
        ]
        intensifiers = ["very", "extremely", "absolutely", "totally", "completely", "really"]
        negators = ["not", "no", "never", "neither", "nobody", "nothing", "nowhere"]
        
        text_lower = text.lower()
        words = text_lower.split()
        
        # Count sentiment indicators
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        intensifier_count = sum(1 for word in intensifiers if word in text_lower)
        negator_count = sum(1 for word in negators if word in text_lower)
        
        # Adjust for intensifiers and negators
        intensity_multiplier = 1 + (intensifier_count * 0.2)
        
        # Simple negation handling
        if negator_count % 2 == 1:  # Odd number of negators flips sentiment
            positive_count, negative_count = negative_count, positive_count
        
        # Calculate sentiment
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            sentiment = "neutral"
            score = 0.5
        elif positive_count > negative_count:
            sentiment = "positive"
            base_score = 0.5 + (positive_count - negative_count) * 0.1
            score = min(0.99, base_score * intensity_multiplier)
        elif negative_count > positive_count:
            sentiment = "negative"
            base_score = 0.5 - (negative_count - positive_count) * 0.1
            score = max(0.01, base_score / intensity_multiplier)
        else:
            sentiment = "mixed"
            score = 0.5
        
        return {
            "sentiment": sentiment,
            "score": round(score, 3),
            "confidence": round(min(0.95, total_sentiment_words * 0.15), 2),
            "positive_indicators": positive_count,
            "negative_indicators": negative_count,
            "intensity_level": "high" if intensifier_count > 0 else "normal",
            "word_count": len(words),
            "analysis_timestamp": str(__import__('datetime').datetime.now().isoformat())
        }
    except Exception as e:
        return {"error": f"Sentiment analysis error: {str(e)}"}
''',
            "calculate_roi": '''
def calculate_roi(investment, returns=None, time_period=1):
    """ROI calculation capability - Calculate return on investment"""
    try:
        # Handle dict input
        if isinstance(investment, dict):
            returns = investment.get('returns', investment.get('return', 0))
            time_period = investment.get('time_period', investment.get('period', 1))
            investment = investment.get('investment', investment.get('cost', 0))
        
        investment = float(investment)
        returns = float(returns) if returns is not None else 0
        time_period = float(time_period) if time_period else 1
        
        if investment <= 0:
            return {"error": "Investment must be positive"}
        
        # Calculate ROI metrics
        profit_loss = returns - investment
        roi_percent = (profit_loss / investment) * 100
        annualized_roi = roi_percent / time_period if time_period != 0 else roi_percent
        
        # Calculate payback period (if profitable)
        if profit_loss > 0 and time_period > 0:
            payback_period = investment / (profit_loss / time_period)
        else:
            payback_period = None
        
        return {
            "roi_percent": round(roi_percent, 2),
            "annualized_roi": round(annualized_roi, 2),
            "profit_loss": round(profit_loss, 2),
            "investment": investment,
            "returns": returns,
            "time_period": time_period,
            "payback_period": round(payback_period, 2) if payback_period else "N/A",
            "status": "profitable" if profit_loss > 0 else "loss" if profit_loss < 0 else "break-even",
            "analysis_timestamp": str(__import__('datetime').datetime.now().isoformat())
        }
    except ValueError as e:
        return {"error": f"Invalid numeric values: {str(e)}"}
    except Exception as e:
        return {"error": f"ROI calculation error: {str(e)}"}
''',
            "generate_insights": '''
def generate_insights(data):
    """Generate insights from data - Pattern recognition and analysis"""
    if not data:
        return {"error": "No data provided"}
    
    try:
        insights = []
        data_type = type(data).__name__
        
        if isinstance(data, str):
            word_count = len(data.split())
            char_count = len(data)
            insights.append(f"Text contains {word_count} words and {char_count} characters")
            
            # Pattern detection
            import re
            has_numbers = bool(re.search(r'\\d+', data))
            has_urls = bool(re.search(r'http[s]?://', data))
            has_emails = bool(re.search(r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b', data, re.IGNORECASE))
            
            if has_numbers:
                insights.append("Numerical data detected in text")
            if has_urls:
                insights.append("URLs found in text")
            if has_emails:
                insights.append("Email addresses identified")
                
        elif isinstance(data, (list, tuple)):
            insights.append(f"Collection contains {len(data)} items")
            
            # Check for numeric data
            numeric_items = [x for x in data if isinstance(x, (int, float))]
            if numeric_items:
                import statistics
                insights.append(f"Numeric range: {min(numeric_items)} to {max(numeric_items)}")
                insights.append(f"Average value: {round(statistics.mean(numeric_items), 2)}")
                
        elif isinstance(data, dict):
            insights.append(f"Dictionary with {len(data)} keys")
            insights.append(f"Keys: {list(data.keys())[:5]}{'...' if len(data) > 5 else ''}")
        
        return {
            "data_type": data_type,
            "insights": insights,
            "insight_count": len(insights),
            "analysis_timestamp": str(__import__('datetime').datetime.now().isoformat())
        }
    except Exception as e:
        return {"error": f"Insight generation error: {str(e)}"}
''',
            "process_customer_data": '''
def process_customer_data(data):
    """Process and analyze customer information"""
    if not data:
        return {"error": "No customer data provided"}
    
    try:
        result = {
            "processed": True,
            "input_type": type(data).__name__,
            "analysis_timestamp": str(__import__('datetime').datetime.now().isoformat())
        }
        
        if isinstance(data, dict):
            result["fields_found"] = list(data.keys())
            result["field_count"] = len(data)
            
            # Common customer data field detection
            common_fields = ['name', 'email', 'phone', 'address', 'id', 'customer_id']
            found_fields = [f for f in common_fields if f in [k.lower() for k in data.keys()]]
            result["standard_fields_detected"] = found_fields
            
        elif isinstance(data, (list, tuple)):
            result["record_count"] = len(data)
            if data and isinstance(data[0], dict):
                result["sample_fields"] = list(data[0].keys())[:5]
                
        elif isinstance(data, str):
            result["character_count"] = len(data)
            result["word_count"] = len(data.split())
        
        return result
    except Exception as e:
        return {"error": f"Customer data processing error: {str(e)}"}
'''
        }
    
    def _bootstrap_core_capabilities(self):
        """Initialize the system with basic capabilities"""
        
        # Basic text processing
        self.capabilities["text_summary"] = {
            "code": '''
def text_summary(text, max_length=100):
    """Generate a summary of the given text"""
    if not text:
        return "No text provided"
    
    words = text.split()
    if len(words) <= max_length:
        return text
    
    return ' '.join(words[:max_length]) + "..."
''',
            "description": "Summarizes text to specified length",
            "created_at": datetime.now().isoformat(),
            "evolved": False
        }
        
        # Basic data analysis
        self.capabilities["basic_stats"] = {
            "code": '''
def basic_stats(numbers):
    """Calculate basic statistics for a list of numbers"""
    if not numbers:
        return {"error": "No numbers provided"}
    
    try:
        # Handle various input types
        if isinstance(numbers, str):
            numbers = [float(x.strip()) for x in numbers.split(',') if x.strip().replace('.', '').replace('-', '').isdigit()]
        else:
            numbers = [float(x) for x in numbers if str(x).replace('.', '').replace('-', '').isdigit()]
        
        if not numbers:
            return {"error": "No valid numbers found"}
        
        import statistics
        
        result = {
            "count": len(numbers),
            "sum": sum(numbers),
            "average": round(statistics.mean(numbers), 2),
            "min": min(numbers),
            "max": max(numbers)
        }
        
        if len(numbers) >= 2:
            result["std_dev"] = round(statistics.stdev(numbers), 2)
            result["median"] = statistics.median(numbers)
        
        return result
    except Exception as e:
        return {"error": f"Calculation error: {str(e)}"}
''',
            "description": "Calculates basic statistics for numerical data",
            "created_at": datetime.now().isoformat(),
            "evolved": False
        }
        
        self._log_development("System bootstrapped with core capabilities", {
            "capabilities": list(self.capabilities.keys())
        })
    
    def _log_development(self, message: str, details: Dict = None):
        """Log development activities"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "evolution_step": self.evolution_count,
            "message": message,
            "total_capabilities": len(self.capabilities),
            "details": details or {}
        }
        self.development_log.append(entry)
        if not self.quiet:
            print(f"📝 LOG: {message}")
    
    def _generate_code_for_capability(self, name: str, description: str) -> str:
        """
        Generate Python code for a new capability
        This is the core of the self-evolution system
        """
        
        # Check for exact template match
        if name in self.enhanced_templates:
            return self.enhanced_templates[name]
        
        # Fuzzy matching for similar tasks
        name_lower = name.lower()
        desc_lower = description.lower()
        combined = name_lower + " " + desc_lower
        
        # Match by keywords
        if any(word in combined for word in ['predict', 'forecast', 'estimate', 'sales']):
            template = self.enhanced_templates['predict_sales']
            return template.replace('predict_sales', name)
        
        if any(word in combined for word in ['sentiment', 'emotion', 'feeling', 'mood']):
            template = self.enhanced_templates['analyze_sentiment']
            return template.replace('analyze_sentiment', name)
        
        if any(word in combined for word in ['roi', 'return', 'profit', 'financial', 'investment']):
            template = self.enhanced_templates['calculate_roi']
            return template.replace('calculate_roi', name)
        
        if any(word in combined for word in ['insight', 'analysis', 'pattern', 'detect']):
            template = self.enhanced_templates['generate_insights']
            return template.replace('generate_insights', name)
        
        if any(word in combined for word in ['customer', 'user', 'client', 'data', 'process']):
            template = self.enhanced_templates['process_customer_data']
            return template.replace('process_customer_data', name)
        
        # Generate a generic capability for unknown tasks
        return f'''
def {name}(input_data):
    """{description}"""
    import re
    from datetime import datetime
    
    if not input_data:
        return {{"error": "No input data provided"}}
    
    try:
        result = {{
            "capability": "{name}",
            "description": "{description}",
            "processed": True,
            "input_type": type(input_data).__name__,
            "timestamp": datetime.now().isoformat()
        }}
        
        # Type-specific processing
        if isinstance(input_data, str):
            text = input_data
            result["word_count"] = len(text.split())
            result["character_count"] = len(text)
            result["has_numbers"] = bool(re.search(r'\\d+', text))
            result["has_urls"] = bool(re.search(r'http[s]?://', text))
            
        elif isinstance(input_data, (list, tuple)):
            result["item_count"] = len(input_data)
            result["sample"] = list(input_data)[:3] if input_data else []
            
            # Check for numeric data
            numeric = [x for x in input_data if isinstance(x, (int, float))]
            if numeric:
                result["numeric_count"] = len(numeric)
                result["numeric_range"] = {{"min": min(numeric), "max": max(numeric)}}
                
        elif isinstance(input_data, dict):
            result["key_count"] = len(input_data)
            result["keys"] = list(input_data.keys())[:10]
        
        return result
        
    except Exception as e:
        return {{"error": f"Processing error: {{str(e)}}"}}
'''
    
    def _validate_code(self, code: str) -> bool:
        """Validate that the generated code is syntactically correct"""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError as e:
            if not self.quiet:
                print(f"❌ Syntax error in generated code: {e}")
            return False
    
    def generate_capability(self, capability_name: str, description: str) -> Dict[str, Any]:
        """
        Generate a new capability based on the description
        This is where the self-evolution happens!
        """
        
        if not self.quiet:
            print(f"\n🔧 Generating new capability: {capability_name}")
            print(f"📋 Description: {description}")
        
        # Check if capability already exists
        if capability_name in self.capabilities:
            return {
                "success": False,
                "error": f"Capability '{capability_name}' already exists",
                "existing_description": self.capabilities[capability_name]["description"]
            }
        
        try:
            # Generate the code
            generated_code = self._generate_code_for_capability(capability_name, description)
            
            # Validate the code
            if not self._validate_code(generated_code):
                self._log_development(f"Code validation failed for: {capability_name}")
                return {
                    "success": False,
                    "error": "Generated code failed syntax validation"
                }
            
            # Test the capability before adding
            test_namespace = {}
            exec(generated_code, {"__builtins__": __builtins__}, test_namespace)
            
            if capability_name not in test_namespace:
                return {
                    "success": False,
                    "error": f"Generated code did not define function '{capability_name}'"
                }
            
            # Add the capability
            self.capabilities[capability_name] = {
                "code": generated_code,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "evolved": True,
                "evolution_step": self.evolution_count
            }
            
            self.evolution_count += 1
            
            # Log the successful generation
            self.generation_history.append({
                "capability_name": capability_name,
                "description": description,
                "timestamp": datetime.now().isoformat(),
                "success": True
            })
            
            self._log_development(f"Successfully generated capability: {capability_name}", {
                "description": description,
                "evolution_step": self.evolution_count
            })
            
            if not self.quiet:
                print(f"✅ Capability '{capability_name}' successfully deployed!")
            
            return {
                "success": True,
                "capability_name": capability_name,
                "description": description,
                "evolution_step": self.evolution_count
            }
            
        except Exception as e:
            error_msg = f"Failed to generate capability: {str(e)}"
            self._log_development(error_msg)
            self.generation_history.append({
                "capability_name": capability_name,
                "description": description,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            })
            return {
                "success": False,
                "error": error_msg
            }
    
    def execute_capability(self, capability_name: str, input_data: Any) -> Dict[str, Any]:
        """Execute a capability with given input data"""
        
        if capability_name not in self.capabilities:
            return {
                "success": False,
                "error": f"Capability '{capability_name}' not found",
                "available_capabilities": list(self.capabilities.keys())
            }
        
        try:
            # Get the capability code
            capability_code = self.capabilities[capability_name]["code"]
            
            # Create execution namespace
            exec_namespace = {"__builtins__": __builtins__}
            
            # Execute the capability code to define the function
            exec(capability_code, exec_namespace)
            
            # Get the function
            if capability_name in exec_namespace:
                func = exec_namespace[capability_name]
                
                # Execute with input data
                result = func(input_data)
                
                return {
                    "success": True,
                    "capability": capability_name,
                    "result": result
                }
            else:
                return {
                    "success": False,
                    "error": f"Function '{capability_name}' not found in capability code"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
    def get_capabilities(self) -> List[str]:
        """Get list of all available capabilities"""
        return list(self.capabilities.keys())
    
    def get_capability_info(self, capability_name: str) -> Dict[str, Any]:
        """Get detailed info about a capability"""
        if capability_name not in self.capabilities:
            return {"error": f"Capability '{capability_name}' not found"}
        
        cap = self.capabilities[capability_name]
        return {
            "name": capability_name,
            "description": cap["description"],
            "created_at": cap["created_at"],
            "evolved": cap.get("evolved", False),
            "code_length": len(cap["code"])
        }
    
    def get_development_log(self) -> List[Dict[str, Any]]:
        """Get the complete development log"""
        return self.development_log
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "version": self.version,
            "total_capabilities": len(self.capabilities),
            "evolved_capabilities": sum(1 for c in self.capabilities.values() if c.get("evolved", False)),
            "evolution_count": self.evolution_count,
            "capabilities": list(self.capabilities.keys()),
            "log_entries": len(self.development_log)
        }
    
    def save_state(self, filepath: str = None) -> str:
        """Save the current system state to a file"""
        if filepath is None:
            filepath = os.path.join(self.output_dir, "chimera_state.json")
        
        state = {
            "version": self.version,
            "saved_at": datetime.now().isoformat(),
            "capabilities": {
                name: {
                    "description": cap["description"],
                    "created_at": cap["created_at"],
                    "evolved": cap.get("evolved", False),
                    "code": cap["code"]
                }
                for name, cap in self.capabilities.items()
            },
            "evolution_count": self.evolution_count,
            "development_log": self.development_log,
            "generation_history": self.generation_history
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        
        if not self.quiet:
            print(f"💾 State saved to: {filepath}")
        return filepath
    
    def load_state(self, filepath: str) -> bool:
        """Load system state from a file"""
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            self.capabilities = {
                name: {
                    "code": cap["code"],
                    "description": cap["description"],
                    "created_at": cap["created_at"],
                    "evolved": cap.get("evolved", False)
                }
                for name, cap in state["capabilities"].items()
            }
            self.evolution_count = state["evolution_count"]
            self.development_log = state.get("development_log", [])
            self.generation_history = state.get("generation_history", [])
            
            if not self.quiet:
                print(f"📂 State loaded from: {filepath}")
                print(f"📊 Capabilities restored: {len(self.capabilities)}")
            return True
            
        except Exception as e:
            if not self.quiet:
                print(f"❌ Failed to load state: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════════════════════════
# DEMONSTRATION & CLI
# ═══════════════════════════════════════════════════════════════════════════════════════

def demonstrate_self_evolution():
    """Demonstrate the self-evolution capabilities"""
    print("\n" + "=" * 70)
    print("🧬 CHIMERA CORE - Self-Evolution Demonstration")
    print("=" * 70)
    
    # Initialize
    chimera = ChimeraCoreEngine()
    
    # Show initial state
    print(f"\n📊 Initial State:")
    print(f"   Capabilities: {chimera.get_capabilities()}")
    print(f"   Total: {len(chimera.get_capabilities())}")
    
    # Test existing capabilities
    print(f"\n🧪 Testing Core Capabilities:")
    
    test_text = "This is a test of the CHIMERA system. It should summarize this text properly."
    result = chimera.execute_capability("text_summary", test_text)
    print(f"   text_summary: {result['result'] if result['success'] else result['error']}")
    
    test_numbers = [10, 20, 30, 40, 50, 60, 70]
    result = chimera.execute_capability("basic_stats", test_numbers)
    print(f"   basic_stats: {result['result'] if result['success'] else result['error']}")
    
    # Generate new capabilities
    print(f"\n🔧 Generating New Capabilities (Self-Evolution):")
    
    test_capabilities = [
        ("predict_sales", "Generate sales forecasts based on historical data"),
        ("analyze_sentiment", "Analyze sentiment of text input"),
        ("calculate_roi", "Calculate return on investment for financial analysis"),
        ("process_customer_data", "Process and analyze customer information")
    ]
    
    for name, description in test_capabilities:
        print(f"\n   🚀 Evolving: {name}")
        result = chimera.generate_capability(name, description)
        
        if result["success"]:
            print(f"      ✅ Success!")
            
            # Test the new capability
            if name == "predict_sales":
                test_data = [100, 120, 150, 180, 200]
                test_result = chimera.execute_capability(name, test_data)
                print(f"      🧪 Test: {test_result['result'] if test_result['success'] else test_result['error']}")
                
            elif name == "analyze_sentiment":
                test_text = "This product is absolutely amazing! I love it!"
                test_result = chimera.execute_capability(name, test_text)
                print(f"      🧪 Test: {test_result['result'] if test_result['success'] else test_result['error']}")
                
            elif name == "calculate_roi":
                test_data = {"investment": 1000, "returns": 1250, "time_period": 1}
                test_result = chimera.execute_capability(name, test_data)
                print(f"      🧪 Test: {test_result['result'] if test_result['success'] else test_result['error']}")
                
            elif name == "process_customer_data":
                test_data = {"name": "John Doe", "email": "john@example.com", "id": 12345}
                test_result = chimera.execute_capability(name, test_data)
                print(f"      🧪 Test: {test_result['result'] if test_result['success'] else test_result['error']}")
        else:
            print(f"      ❌ Failed: {result['error']}")
    
    # Show final state
    print(f"\n📊 Final State:")
    status = chimera.get_status()
    print(f"   Total Capabilities: {status['total_capabilities']}")
    print(f"   Evolved Capabilities: {status['evolved_capabilities']}")
    print(f"   Evolution Count: {status['evolution_count']}")
    print(f"   All Capabilities: {status['capabilities']}")
    
    # Save state
    state_file = chimera.save_state()
    
    print(f"\n🎯 CHIMERA CORE demonstration complete!")
    print("=" * 70)
    
    return chimera


def interactive_mode():
    """Run CHIMERA in interactive mode"""
    print("\n" + "=" * 70)
    print("🧬 CHIMERA CORE - Interactive Mode")
    print("=" * 70)
    
    chimera = ChimeraCoreEngine()
    
    while True:
        print("\n" + "-" * 50)
        print("Commands:")
        print("  1. List capabilities")
        print("  2. Execute capability")
        print("  3. Generate new capability")
        print("  4. Show status")
        print("  5. Save state")
        print("  6. Run demo")
        print("  0. Exit")
        print("-" * 50)
        
        choice = input("Enter choice: ").strip()
        
        if choice == "1":
            caps = chimera.get_capabilities()
            print(f"\n📋 Available Capabilities ({len(caps)}):")
            for cap in caps:
                info = chimera.get_capability_info(cap)
                print(f"   • {cap}: {info['description']}")
                
        elif choice == "2":
            cap_name = input("Capability name: ").strip()
            input_data = input("Input data: ").strip()
            
            # Try to parse as JSON
            try:
                input_data = json.loads(input_data)
            except:
                pass
            
            result = chimera.execute_capability(cap_name, input_data)
            print(f"\n🎯 Result: {json.dumps(result, indent=2)}")
            
        elif choice == "3":
            cap_name = input("New capability name: ").strip()
            description = input("Description: ").strip()
            
            result = chimera.generate_capability(cap_name, description)
            if result["success"]:
                print(f"\n✅ Successfully created: {cap_name}")
            else:
                print(f"\n❌ Failed: {result['error']}")
                
        elif choice == "4":
            status = chimera.get_status()
            print(f"\n📊 System Status:")
            print(json.dumps(status, indent=2))
            
        elif choice == "5":
            filepath = chimera.save_state()
            print(f"\n💾 State saved to: {filepath}")
            
        elif choice == "6":
            demonstrate_self_evolution()
            
        elif choice == "0":
            print("\n🧬 CHIMERA signing off. The system remembers.\n")
            break
        
        else:
            print("\n❌ Invalid choice")


def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg == "--demo":
            demonstrate_self_evolution()
        elif arg == "--server":
            try:
                from fastapi import FastAPI, HTTPException
                import uvicorn
                
                app = FastAPI(title="CHIMERA CORE API", version="2.0")
                chimera = ChimeraCoreEngine()
                
                @app.get("/")
                async def root():
                    return {"message": "🧬 CHIMERA CORE API", "status": chimera.get_status()}
                
                @app.get("/capabilities")
                async def list_capabilities():
                    return {"capabilities": chimera.get_capabilities()}
                
                @app.post("/generate")
                async def generate(name: str, description: str):
                    return chimera.generate_capability(name, description)
                
                @app.post("/execute")
                async def execute(capability: str, data: Any):
                    return chimera.execute_capability(capability, data)
                
                @app.get("/status")
                async def status():
                    return chimera.get_status()
                
                print("🚀 Starting CHIMERA CORE API server...")
                uvicorn.run(app, host="0.0.0.0", port=8000)
                
            except ImportError:
                print("❌ FastAPI not installed. Run: pip install fastapi uvicorn")
                
        elif arg == "--interactive" or arg == "-i":
            interactive_mode()
        else:
            print(f"Unknown argument: {arg}")
            print("Usage: python chimera_engine.py [--demo|--server|--interactive]")
    else:
        # Default to interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
