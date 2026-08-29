from app.ai_drift import analyze_drift
# Imports our AI drift analysis function.


router = "R3"
# Tells NetPilot which router has the problem.


missing = ["ip ospf 1 area 0"]
# This is what the golden configuration expects.


added = ["ip ospf 1 area 1"]
# This is what we found on the live router.


answer = analyze_drift(router, missing, added)
# Sends the configuration difference to Qwen.


print()
# Prints a blank line.


print("===== NETPILOT AI DIAGNOSIS =====")
# Prints a heading.


print(answer)
# Displays Qwen's answer.