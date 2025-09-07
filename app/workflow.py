from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Dict, Any

# Import all three agents now
from agents.agent_b import AgentB
from agents.agent_c import AgentC
from agents.agent_d import AgentD

# The state now includes all possible fields from all agents
class WorkflowState(TypedDict, total=False):
    session_id: str
    user_id: str
    file_path: str
    filename: str
    risk_assessment: Dict[str, Any]
    user_approved: bool
    meeting_date: str
    signing_result: Dict[str, Any]
    scheduling_result: Dict[str, Any]
    workflow_complete: bool
    final_status: str
    error: str
    waiting_for_input: bool
    input_type: str
    document_signed: bool
    meeting_scheduled: bool
    signing_timestamp: str

class DocumentWorkflow:
    def __init__(self):
        self.agent_b = AgentB()
        self.agent_c = AgentC()
        self.agent_d = AgentD()
        self.memory = MemorySaver()
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        workflow = StateGraph(WorkflowState)

        # Add all nodes, including the new one for Agent B
        workflow.add_node("agent_b_analyze", self._agent_b_analyze)
        workflow.add_node("wait_for_approval", self._wait_for_approval)
        workflow.add_node("agent_c_sign", self._agent_c_sign)
        workflow.add_node("wait_for_meeting_date", self._wait_for_meeting_date)
        workflow.add_node("agent_d_schedule", self._agent_d_schedule)
        workflow.add_node("handle_rejection", self._handle_rejection)
        workflow.add_node("complete", self._complete)

        # The workflow now starts with Agent B's analysis
        workflow.set_entry_point("agent_b_analyze")
        
        # Define the new workflow path
        workflow.add_edge("agent_b_analyze", "wait_for_approval")
        workflow.add_conditional_edges("wait_for_approval", self._decide_after_approval)
        workflow.add_edge("agent_c_sign", "wait_for_meeting_date")
        workflow.add_edge("wait_for_meeting_date", "agent_d_schedule")
        workflow.add_edge("agent_d_schedule", "complete")
        workflow.add_edge("handle_rejection", END)
        workflow.add_edge("complete", END)

        return workflow.compile(
            checkpointer=self.memory,
            interrupt_before=["wait_for_approval", "wait_for_meeting_date"]
        )

    # --- Node Functions ---

    def _agent_b_analyze(self, state: WorkflowState) -> WorkflowState:
        """Node to run Agent B for initial risk assessment."""
        print(f"[{self.agent_b.agent_name}] Analyzing file: {state['file_path']}")
        risk_assessment = self.agent_b.analyze_file(state['file_path'])
        return {"risk_assessment": risk_assessment}

    def _wait_for_approval(self, state: WorkflowState) -> WorkflowState:
        """Pauses for human approval."""
        return {"waiting_for_input": True, "input_type": 'approval'}

    def _decide_after_approval(self, state: WorkflowState) -> str:
        """Decides where to go after the user provides approval input."""
        return "agent_c_sign" if state.get('user_approved') else "handle_rejection"

    def _agent_c_sign(self, state: WorkflowState) -> WorkflowState:
        """Runs Agent C to sign the document."""
        if not self.agent_c.validate_signing_requirements(state):
            return {"error": "Signing requirements not met.", "final_status": "FAILED"}
        return self.agent_c.sign_document(state)

    def _wait_for_meeting_date(self, state: WorkflowState) -> WorkflowState:
        """Pauses for the user to provide a meeting date."""
        if not state.get("document_signed"):
             return {"error": "Document not signed, cannot schedule meeting.", "final_status": "FAILED"}
        return {"waiting_for_input": True, "input_type": 'meeting_date'}

    def _agent_d_schedule(self, state: WorkflowState) -> WorkflowState:
        """Runs Agent D to schedule the meeting."""
        return self.agent_d.schedule_meeting(state)

    def _handle_rejection(self, state: WorkflowState) -> WorkflowState:
        """Handles the case where the user rejects the document."""
        return {"final_status": "REJECTED", "workflow_complete": True}
        
    def _complete(self, state: WorkflowState) -> WorkflowState:
        """Final node to mark the workflow as complete."""
        status = "SUCCESS" if state.get("meeting_scheduled") else "FAILED"
        return {"final_status": status, "workflow_complete": True}

    # --- Workflow Interaction Methods ---

    def start_workflow(self, initial_state: WorkflowState):
        """Starts the workflow with an initial state."""
        thread_config = {"configurable": {"thread_id": initial_state['session_id']}}
        return self.workflow.invoke(initial_state, thread_config)

    def continue_workflow(self, session_id: str, human_input: dict):
        """Resumes a paused workflow with human input."""
        thread_config = {"configurable": {"thread_id": session_id}}
        return self.workflow.invoke(human_input, thread_config)

    def get_workflow_state(self, session_id: str):
        """Retrieves the current state of a workflow."""
        thread_config = {"configurable": {"thread_id": session_id}}
        state = self.workflow.get_state(thread_config)
        return state.values if state else None