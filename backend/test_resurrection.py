from lazarus_agent import process_resurrection

# Mock Data
repo_url = "https://github.com/ArunN2005/demo-repo"
vibe = "Fix the broken HTML and make it Cyberpunk"

print(f"Testing Lazarus with: {repo_url}")
print("-" * 50)

# Run the agent
result = process_resurrection(repo_url, vibe)

print(result)
print("-" * 50)
print("Test Complete.")
