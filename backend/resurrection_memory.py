"""
Lazarus Engine - Resurrection Memory System
Time-Persistent Memory for Cross-Session Learning

This module provides persistent memory for each repository,
storing past resurrection attempts, failures, and decisions.
Gemini uses this to make smarter choices on subsequent resurrections.
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, List

# Memory storage directory
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "resurrection_memory")

def get_repo_id(repo_url: str) -> str:
    """Generate a unique ID for a repository URL."""
    # Normalize the URL
    normalized = repo_url.lower().strip().rstrip('/')
    # Create a hash for privacy and filesystem safety
    return hashlib.md5(normalized.encode()).hexdigest()[:16]

def get_memory_path(repo_url: str) -> str:
    """Get the path to the memory file for a repository."""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    return os.path.join(MEMORY_DIR, f"{get_repo_id(repo_url)}_memory.json")

def load_memory(repo_url: str) -> Dict:
    """
    Load the resurrection memory for a repository.
    Returns empty memory if none exists.
    """
    path = get_memory_path(repo_url)
    
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Memory load warning: {e}")
            return create_empty_memory(repo_url)
    
    return create_empty_memory(repo_url)

def create_empty_memory(repo_url: str) -> Dict:
    """Create a new empty memory structure."""
    return {
        "repo_url": repo_url,
        "repo_id": get_repo_id(repo_url),
        "created_at": datetime.now().isoformat(),
        "last_resurrection": None,
        "total_attempts": 0,
        "successful_attempts": 0,
        "failed_attempts": 0,
        
        # Tech Stack Memory
        "tech_stack": {
            "detected_backend": None,
            "detected_frontend": None,
            "detected_database": None,
            "preferred_modernization": None
        },
        
        # Decision History
        "decisions": [],
        
        # Failure Memory (Critical for learning)
        "failures": [],
        
        # Dependency Pain Points
        "dependency_issues": [],
        
        # Successful Patterns
        "successful_patterns": [],
        
        # User Preferences
        "user_preferences": {
            "keep_original_paths": True,
            "preferred_css_framework": None,
            "preferred_frontend_framework": None,
            "avoid_frameworks": []
        },
        
        # Resurrection History
        "resurrection_history": []
    }

def save_memory(repo_url: str, memory: Dict) -> bool:
    """Save the resurrection memory for a repository."""
    path = get_memory_path(repo_url)
    
    try:
        os.makedirs(MEMORY_DIR, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[!] Memory save error: {e}")
        return False

def record_attempt_start(repo_url: str, tech_stack: Dict = None) -> Dict:
    """
    Record the start of a resurrection attempt.
    Returns the current memory state.
    """
    memory = load_memory(repo_url)
    
    memory["total_attempts"] += 1
    memory["last_resurrection"] = datetime.now().isoformat()
    
    # Update tech stack if provided
    if tech_stack:
        memory["tech_stack"]["detected_backend"] = tech_stack.get("backend", {}).get("framework")
        memory["tech_stack"]["detected_frontend"] = tech_stack.get("frontend", {}).get("framework")
        memory["tech_stack"]["detected_database"] = tech_stack.get("backend", {}).get("database")
    
    save_memory(repo_url, memory)
    return memory

def record_failure(repo_url: str, error_type: str, error_message: str, context: str = "") -> None:
    """
    Record a failure for learning.
    This helps Gemini avoid the same mistakes next time.
    """
    memory = load_memory(repo_url)
    
    memory["failed_attempts"] += 1
    
    failure = {
        "timestamp": datetime.now().isoformat(),
        "error_type": error_type,
        "error_message": error_message[:500],  # Truncate long errors
        "context": context[:300],
        "lesson_learned": generate_lesson(error_type, error_message)
    }
    
    # Keep last 10 failures
    memory["failures"].append(failure)
    memory["failures"] = memory["failures"][-10:]
    
    save_memory(repo_url, memory)

def record_success(repo_url: str, decisions: List[str] = None, patterns_used: List[str] = None) -> None:
    """
    Record a successful resurrection.
    This reinforces good decisions.
    """
    memory = load_memory(repo_url)
    
    memory["successful_attempts"] += 1
    
    if decisions:
        for decision in decisions:
            memory["decisions"].append({
                "timestamp": datetime.now().isoformat(),
                "decision": decision,
                "outcome": "success"
            })
        # Keep last 20 decisions
        memory["decisions"] = memory["decisions"][-20:]
    
    if patterns_used:
        for pattern in patterns_used:
            if pattern not in memory["successful_patterns"]:
                memory["successful_patterns"].append(pattern)
        # Keep last 15 patterns
        memory["successful_patterns"] = memory["successful_patterns"][-15:]
    
    history_entry = {
        "timestamp": datetime.now().isoformat(),
        "outcome": "success",
        "decisions": decisions or []
    }
    memory["resurrection_history"].append(history_entry)
    memory["resurrection_history"] = memory["resurrection_history"][-10:]
    
    save_memory(repo_url, memory)

def record_dependency_issue(repo_url: str, package: str, issue: str) -> None:
    """Record a dependency pain point."""
    memory = load_memory(repo_url)
    
    issue_record = {
        "package": package,
        "issue": issue,
        "timestamp": datetime.now().isoformat()
    }
    
    # Avoid duplicates
    existing = [d["package"] for d in memory["dependency_issues"]]
    if package not in existing:
        memory["dependency_issues"].append(issue_record)
    
    save_memory(repo_url, memory)

def record_decision(repo_url: str, decision: str, reasoning: str = "") -> None:
    """Record a tech decision made during resurrection."""
    memory = load_memory(repo_url)
    
    memory["decisions"].append({
        "timestamp": datetime.now().isoformat(),
        "decision": decision,
        "reasoning": reasoning,
        "outcome": "pending"
    })
    
    save_memory(repo_url, memory)

def generate_lesson(error_type: str, error_message: str) -> str:
    """Generate a lesson learned from an error."""
    lessons = {
        "NODE_MODULE_NOT_FOUND": "Ensure npm install runs in the correct directory where dependencies are expected.",
        "FRONTEND_BUILD_ERROR": "Check for TypeScript errors and missing dependencies before building.",
        "NODE_CRASH": "Verify all required modules are installed and paths are correct.",
        "MONGODB_CONNECTION_ERROR": "MongoDB connection string may need updating or the database server may be unreachable.",
        "SYNTAX_ERROR": "Code has syntax issues - review generated code for typos.",
        "PORT_IN_USE": "The port is already in use - try a different port.",
        "FILE_NOT_FOUND": "A required file is missing - check file paths.",
        "PYTHON_IMPORT_ERROR": "Python module not installed - add to requirements.txt.",
        "BACKEND_CRASH": "Server crashed on startup - check logs for details.",
    }
    
    for error_key, lesson in lessons.items():
        if error_key in error_type:
            return lesson
    
    return "Review the error and adjust the approach accordingly."

def get_memory_context_for_prompt(repo_url: str) -> str:
    """
    Generate a context string from memory for the AI prompt.
    This is the key function that injects past learnings into Gemini.
    """
    memory = load_memory(repo_url)
    
    # If no past resurrections, return minimal context
    if memory["total_attempts"] == 0:
        return ""
    
    context = f"""
████████████████████████████████████████████████████████████████████████████████
█ 🧠 RESURRECTION MEMORY (This repository has been resurrected before!)
████████████████████████████████████████████████████████████████████████████████

📊 PAST RESURRECTION STATISTICS:
   - Total Attempts: {memory["total_attempts"]}
   - Successful: {memory["successful_attempts"]}
   - Failed: {memory["failed_attempts"]}
   - Last Resurrection: {memory["last_resurrection"]}

"""
    
    # Add failure learnings (most important!)
    if memory["failures"]:
        context += """
⚠️ PAST FAILURES (AVOID THESE MISTAKES!):
"""
        for failure in memory["failures"][-5:]:  # Last 5 failures
            context += f"""
   ❌ {failure["error_type"]}: {failure["error_message"][:100]}
      💡 Lesson: {failure["lesson_learned"]}
"""
    
    # Add successful patterns
    if memory["successful_patterns"]:
        context += """
✅ SUCCESSFUL PATTERNS (USE THESE AGAIN):
"""
        for pattern in memory["successful_patterns"]:
            context += f"   ✓ {pattern}\n"
    
    # Add dependency issues
    if memory["dependency_issues"]:
        context += """
📦 DEPENDENCY PAIN POINTS (HANDLE CAREFULLY):
"""
        for issue in memory["dependency_issues"]:
            context += f"   ⚠️ {issue['package']}: {issue['issue']}\n"
    
    # Add recent decisions
    if memory["decisions"]:
        context += """
🎯 PAST DECISIONS:
"""
        for decision in memory["decisions"][-5:]:
            outcome_emoji = "✓" if decision.get("outcome") == "success" else "○"
            context += f"   {outcome_emoji} {decision['decision']}\n"
    
    # Add tech stack memory
    if memory["tech_stack"]["detected_backend"]:
        context += f"""
🔧 REMEMBERED TECH STACK:
   - Backend: {memory["tech_stack"]["detected_backend"]}
   - Frontend: {memory["tech_stack"]["detected_frontend"]}
   - Database: {memory["tech_stack"]["detected_database"]}
"""
    
    context += """
████████████████████████████████████████████████████████████████████████████████

USE THIS MEMORY TO MAKE BETTER DECISIONS!
- Avoid patterns that failed before
- Repeat patterns that succeeded
- Handle known dependency issues proactively

"""
    
    return context

def get_memory_summary(repo_url: str) -> Dict:
    """Get a summary of the memory for API responses."""
    memory = load_memory(repo_url)
    
    return {
        "total_attempts": memory["total_attempts"],
        "successful_attempts": memory["successful_attempts"],
        "failed_attempts": memory["failed_attempts"],
        "last_resurrection": memory["last_resurrection"],
        "has_past_failures": len(memory["failures"]) > 0,
        "has_learned_patterns": len(memory["successful_patterns"]) > 0
    }

def clear_memory(repo_url: str) -> bool:
    """Clear the memory for a repository (for testing/reset)."""
    path = get_memory_path(repo_url)
    
    if os.path.exists(path):
        try:
            os.remove(path)
            return True
        except Exception as e:
            print(f"[!] Memory clear error: {e}")
            return False
    
    return True
