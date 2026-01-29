# Flink Job: LongestSessionPerJob Implementation Plan

## Objective
Implement a Flink streaming job that identifies task SUBMIT event groupings (stages) for each job, where a stage ends when there's 10 minutes (600 seconds) of inactivity with no SUBMIT events. Output the job ID and the count of tasks in the longest stage.

## Data Schema Understanding

### Task Events (Input 1)
- Columns: timestamp(us), missing_info, job_id, task_index, machine_id, event_type, user, class, priority, cpu, memory, disk, machines_restriction
- SUBMIT events have: event_type = 0, empty machine_id
- Timestamps in microseconds since trace start

### Job Events (Input 2)
- Columns: timestamp(us), missing_info, job_id, event_type, user, class, job_name, logical_job_name
- Used to determine when jobs finish (event_type = 4)
- Allows us to know when to finalize stage calculations

## Implementation Strategy

### 1. Data Types to Create (clusterdata.datatypes package)

#### TaskEvent class
- timestamp: long (microseconds)
- jobId: long
- taskIndex: long
- eventType: int
- All other fields for completeness (user, priority, etc.)
- Constructor, getters, equals, hashCode, toString

#### JobEvent class
- timestamp: long (microseconds)
- jobId: long
- eventType: int
- All other fields for completeness
- Constructor, getters, equals, hashCode, toString

### 2. Core Algorithm Design

**Problem:** Identify consecutive SUBMIT events within 10-minute (600 second) windows
- 10 minutes = 600 seconds = 600,000,000 microseconds
- A stage ends when no SUBMIT events occur for 600,000,000 microseconds

**Approach:**
1. Read task events from gzipped CSV → deserialize to TaskEvent objects
2. Filter for SUBMIT events only (event_type == 0)
3. For each job (key by jobId):
   - Sort SUBMIT events by timestamp
   - Group into stages: consecutive events within 10-minute windows
   - Track task count per stage using task_index
   - Remember the longest stage
4. Read job events and filter for job FINISH events (event_type == 4)
5. Use co-process/window operators to:
   - Accumulate SUBMIT events into stages by jobId
   - Emit longest stage count only when job FINISH event arrives
6. Output format: (jobId, maxTasksInAnyStage)

### 3. Implementation Details

#### File: /app/workspace/src/main/java/clusterdata/datatypes/TaskEvent.java
- Parse CSV: fields[0]=timestamp, fields[2]=jobId, fields[3]=taskIndex, fields[5]=eventType
- Convert timestamp from String to long (microseconds)
- POJO with Flink-serializable types

#### File: /app/workspace/src/main/java/clusterdata/datatypes/JobEvent.java
- Parse CSV: fields[0]=timestamp, fields[2]=jobId, fields[3]=eventType
- Convert timestamp from String to long (microseconds)
- POJO with Flink-serializable types

#### File: /app/workspace/src/main/java/clusterdata/query/LongestSessionPerJob.java
Main implementation:

1. **Source Setup:**
   - TextInputFormat to read gzipped task_events CSV
   - TextInputFormat to read gzipped job_events CSV
   - Parse each line to TaskEvent / JobEvent POJOs

2. **Processing Stages:**
   - Filter task stream for event_type == 0 (SUBMIT only)
   - Key by jobId
   - Use custom Aggregator / ProcessFunction to track stages
   - Track timing gaps between consecutive events
   - Emit stage boundaries when 10-min gap detected

3. **State Management:**
   - Use MapState or ListState to store:
     - List of (timestamp, taskIndex) for current stage
     - Maximum task count seen across all completed stages
   - Keyed by jobId

4. **Windowing Strategy:**
   - Use TimeoutFunction / ProcessFunction with state instead of tumbling/sliding windows
   - Process events in order by timestamp
   - When gap > 600 seconds detected: finalize current stage, start new one
   - When job FINISH event received: emit final result

5. **Output:**
   - Format: "(jobId,maxTaskCount)" per line
   - Write to specified output path using TextOutputFormat
   - One result per unique job that had SUBMIT events

### 4. Critical Implementation Notes

- **Timestamps:** Microseconds must be converted to proper time units (divide by 1,000,000 for seconds)
- **10-minute threshold:** 600 seconds = 600,000,000 microseconds
- **Task counting:** Count unique or all SUBMIT events (if task resubmitted = separate count per task spec)
  - Per requirement: "if same task submitted then failed/evicted and resubmitted again, these should be counted separately"
- **Job matching:** Only count stages for jobs where both task events AND job events exist
- **Parsing:** Handle gzipped CSV with proper UTF-8 encoding
- **Empty fields:** Some CSV fields are empty (e.g., machine_id for SUBMIT)

### 5. Files to Create/Modify

1. **Create:** `/app/workspace/src/main/java/clusterdata/datatypes/TaskEvent.java`
   - POJO class for task events

2. **Create:** `/app/workspace/src/main/java/clusterdata/datatypes/JobEvent.java`
   - POJO class for job events

3. **Modify:** `/app/workspace/src/main/java/clusterdata/query/LongestSessionPerJob.java`
   - Implement full pipeline
   - Read both inputs, filter for submission/finish events
   - Calculate longest stage per job
   - Write output in required format

### 6. Testing & Verification

1. **Compilation:** `mvn clean package` should produce JAR with no errors
2. **Manual Testing:**
   - Verify TaskEvent/JobEvent POJOs parse sample CSV lines correctly
   - Test stage grouping logic with mock data
   - Verify 10-minute threshold timing
3. **Integration Test:**
   - Run job on sample data:
     ```
     flink run LongestSessionPerJob.jar \
       --task_input /app/workspace/data/task_events/part-00001-of-00500.csv.gz \
       --job_input /app/workspace/data/job_events/part-00001-of-00500.csv.gz \
       --output /tmp/output.txt
     ```
   - Verify output format: each line is `(jobId,taskCount)`
   - Verify all jobs with task events are represented
   - Spot-check stage calculations manually

## Risk Mitigation

1. **Memory:** Use state management (not collecting all events in-memory)
2. **Ordering:** Ensure events processed in timestamp order (may need sorting)
3. **Late Data:** Ignore events with timestamps > current processing time
4. **CSV Parsing:** Use try-catch, skip malformed lines with logging
5. **Edge Cases:**
   - Jobs with no SUBMIT events: skip
   - Jobs with single SUBMIT: stage count = 1
   - Jobs with no FINISH event: emit result on job timeout or at end

## Dependencies
- Flink 1.18.0 (streaming API)
- Standard Java types only (no extra libraries needed)
