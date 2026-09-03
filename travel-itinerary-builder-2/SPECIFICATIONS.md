# Travel Itinerary Builder

## Overview
Build Travel Itinerary Builder as an autonomous, multi-agent AI pipeline designed to generate structured, multi-day vacation plans.
1. The app will ask the user for city of origin, destination, interests, budget, departure date (optional), and duration then produce a complete itinerary.
2. The app will group the activities geographically each day to prevent excessive travel time.
3. The app will enforce strict budgetary boundaries.
3. Build the app to use Gemini API.
4. Create a README.md file to show how to run the app and how the app works

## Implementation Requirements
1. It should get the API Key from the environment variable GEMINI_API_KEY, model name from the environment variable GEMINI_MODEL, and fallback model name from the environment variable GEMINI_FALLBACK_MODEL. Use the fallback model name if the primary model name is not available.
2. Use flask to build this application. Once the user submits the form, it will start generating the itinerary and display it in a user-friendly format in the same page.
3. Store the information from each user request in a CSV file named usages.csv in the artifacts folder.
4. Store the all the details about the interactions between agent, skills, tools, model invocations, and etc in a file named events.json in the artifacts folder. Include actual payload sent between entities and models. The event logs should be store in a single line.
5. Create a button to allow the user to download the generated itinerary as a text or PDF file.
6. There should be a button or tab at the top of the page to switch between the current itinerary and the history of itineraries and the event logs.
7. The Itineraries & Events logs page should show the the counts of itineraries created, successful runs, failed runs, and the number of event logs stored.
8. Below the summary, there should be a table showing the itineraries created. Each row of the itinerary should show all the details for each run including the date and time it was created, the number of event logs created for that run.
9. When the row is clicked, it should display the full itinerary for that run in a pop up window.
10. When the events count in each row is clicked, all the event logs for that run should be shown in the second table below the itinerary table. Each row of the event log should show all the details for each request including the timestamp, event type, agent/source of the event, a short summary of the event log, and a "Payload" button to show details about the event log.
11. When the "Payload" button is clicked, it should display the full payload for that event log in a pop up window.
12. The pop up window should include a button to allow the user to copy the contents of the payload to the clipboard.

## Architecture
The application follows a hybrid orchestration pattern, utilizing a **Sequential Pipeline** that coordinates a **Parallel Discovery Phase** followed by an iterative **Loop Refinement Phase**.

### 1. Parallel Agent (Discovery Team)
Orchestrated by the `ParallelAgent`, the following sub-agents execute concurrently:
- **FlightResearcher:** Locates transport, travel times, and costs.
- **HotelResearcher:** Finds lodging matching interests and neighborhood safety.
- **ActivityPlanner:** Compiles landmarks, restaurants, and tours.

### 3. Loop Agent (Optimization Room)
Orchestrated by the `LoopAgent`, these agents refine the itinerary:
- **Scheduler:** Reads research, builds the day-by-day sequence, group daiy activities to make sure they are geographically close and efficient to travel between, and calculates total costs. Implement Gemini skills in this agent to make the itinerary more interesting and fun for the user.
- **BudgetEnforcer:** Validates the itinerary against the user's budget.

### Loop Constraints
- **Success:** If cost ≤ budget, `budget_approved` is set to `true` and the loop terminates.
- **Failure:** If cost > budget, the agent provides `critic_feedback` (e.g., "Replace 5-star hotel with 3-star"), sets `budget_approved` to `false`, and triggers the Scheduler for the next iteration.
- **Cap:** Maximum of 3 iterations.

## Global State Schema
All agents interact with a single, centralized dictionary state:

```json
{
  "user_input": {
    "destination": "string",
    "budget": "float",
    "days": "integer",
    "interests": ["string"]
  },
  "raw_research": {
    "flights": [],
    "hotels": [],
    "activities": []
  },
  "current_itinerary": {
    "total_estimated_cost": "float",
    "schedule": [
      {
        "day": "integer",
        "events": []
      }
    ]
  },
  "critic_feedback": "string",
  "budget_approved": "boolean"
}
```

##  Quality Evaluation

The implementation is evaluated based on three milestones:

- **Structural Integrity (40%)**: Must explicitly declare ParallelAgent and LoopAgent frameworks.
- **Context Extraction & State Management (40%)**: The Scheduler must read critic_feedback from prior iterations to modify the trip successfully.
- **Graceful Failure Handling (20%)**: Must handle impossible inputs (e.g., extremely low budgets) without crashing.
