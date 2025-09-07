from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt
from typing import TypedDict, Dict, Any
from agents.agent_c import AgentC
from agents.agent_d import AgentD

class WorkflowState(TypedDict):
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
    human_input: Any
    next_node: str
    # ADDED MISSING FIELDS
    document_signed: bool
    meeting_scheduled: bool
    signing_timestamp: str
    next_agent: str

class DocumentWorkflow:
    """LangGraph workflow manager with proper human-in-the-loop support"""
    
    def __init__(self):
        self.agent_c = AgentC()
        self.agent_d = AgentD()
        self.memory = MemorySaver()
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        """Build the LangGraph workflow with interrupt-based waiting"""
        workflow = StateGraph(WorkflowState)

        # Add nodes
        workflow.add_node("wait_for_approval", self._wait_for_approval)
        workflow.add_node("wait_for_meeting_date", self._wait_for_meeting_date)
        workflow.add_node("agent_c_sign", self._agent_c_sign)
        workflow.add_node("agent_d_schedule", self._agent_d_schedule)
        workflow.add_node("complete", self._complete)

        # Add edges
        workflow.add_edge("wait_for_approval", "wait_for_meeting_date")
        workflow.add_edge("wait_for_meeting_date", "agent_c_sign")
        workflow.add_edge("agent_c_sign", "agent_d_schedule")
        workflow.add_edge("agent_d_schedule", "complete")
        workflow.add_edge("complete", END)

        workflow.set_entry_point("wait_for_approval")

        return workflow.compile(checkpointer=self.memory)

    def _wait_for_approval(self, state):
        """Wait for human approval using interrupt"""
        print("[Workflow] Waiting for user approval...")
        state['waiting_for_input'] = True
        state['input_type'] = 'approval'
        state['next_node'] = 'wait_for_approval'
        
        # Pause execution and wait for resume with user input
        user_input = interrupt("Waiting for approval decision")
        
        # The user input comes through the resume mechanism
        # It will be the actual input data passed to continue_workflow
        if isinstance(user_input, dict) and 'approved' in user_input:
            state['user_approved'] = user_input['approved']
        else:
            state['user_approved'] = user_input if isinstance(user_input, bool) else False
        
        state['waiting_for_input'] = False
        print(f"[Workflow] Approval received: {state['user_approved']}")
        
        return state

    def _wait_for_meeting_date(self, state):
        """Wait for meeting date input using interrupt"""
        print(f"[Workflow] Checking approval status: {state.get('user_approved')}")
        
        # Only proceed if user approved
        if not state.get('user_approved', False):
            print("[Workflow] User did not approve, completing workflow")
            state['workflow_complete'] = True
            state['final_status'] = 'REJECTED'
            state['waiting_for_input'] = False
            return state

        print("[Workflow] Waiting for meeting date...")
        state['waiting_for_input'] = True
        state['input_type'] = 'meeting_date'
        state['next_node'] = 'wait_for_meeting_date'
        
        # Pause execution and wait for resume with user input
        user_input = interrupt("Waiting for meeting date")
        
        # The user input comes through the resume mechanism
        if isinstance(user_input, dict) and 'meeting_date' in user_input:
            state['meeting_date'] = user_input['meeting_date']
        else:
            state['meeting_date'] = str(user_input) if user_input else ''
        
        state['waiting_for_input'] = False
        print(f"[Workflow] Meeting date received: {state['meeting_date']}")
        
        return state

    def _agent_c_sign(self, state):
        """Execute Agent C (Document Signing)"""
        print("[Workflow] Executing Agent C - Document Signing")
        print(f"[DEBUG] BEFORE Agent C - document_signed: {state.get('document_signed', 'NOT SET')}")
        
        state['waiting_for_input'] = False
        
        if not self.agent_c.validate_signing_requirements(state):
            state['error'] = "Document signing requirements not met"
            state['workflow_complete'] = True
            state['final_status'] = 'FAILED'
            return state

        # Get updated state from Agent C
        updated_state = self.agent_c.sign_document(state)
        print(f"[DEBUG] AFTER Agent C - document_signed: {updated_state.get('document_signed', 'NOT SET')}")
        print(f"[DEBUG] Agent C signing_result status: {updated_state.get('signing_result', {}).get('status', 'NO STATUS')}")
        
        return updated_state

    def _agent_d_schedule(self, state):
        """Execute Agent D (Calendar Scheduling)"""
        print("[Workflow] Executing Agent D - Calendar Scheduling")
        
        # Check BOTH document_signed flag AND signing_result status
        document_signed = (state.get('document_signed', False) or 
                        state.get('signing_result', {}).get('status') == 'SIGNED')
        
        print(f"[DEBUG] document_signed flag: {state.get('document_signed', 'NOT SET')}")
        print(f"[DEBUG] signing_result status: {state.get('signing_result', {}).get('status', 'NO STATUS')}")
        print(f"[DEBUG] Final decision - document is signed: {document_signed}")
        
        if not document_signed:
            state['error'] = "Cannot schedule meeting - document not signed"
            state['workflow_complete'] = True
            state['final_status'] = 'FAILED'
            return state

        updated_state = self.agent_d.schedule_meeting(state)
        return updated_state

    def _complete(self, state):
        """Complete the workflow"""
        print("[Workflow] Workflow completed")
        state['waiting_for_input'] = False
        state['workflow_complete'] = True
        
        if not state.get('error'):
            if state.get('meeting_scheduled', False):
                state['final_status'] = 'SUCCESS'
            else:
                state['final_status'] = 'PARTIAL_SUCCESS'
        
        return state

    def start_workflow(self, initial_state: WorkflowState) -> WorkflowState:
        """Start the workflow and return first waiting state"""
        try:
            print(f"[Workflow] Starting workflow for session: {initial_state.get('session_id')}")
            thread_config = {"configurable": {"thread_id": initial_state['session_id']}}
            
            # Initialize missing fields with default values
            initial_state.setdefault('document_signed', False)
            initial_state.setdefault('meeting_scheduled', False)
            initial_state.setdefault('signing_timestamp', '')
            initial_state.setdefault('next_agent', '')
            
            # Start the workflow - it will pause at first interrupt()
            result = self.workflow.invoke(
                input=initial_state,
                config={**thread_config, "recursion_limit": 100}
            )
            
            return result

        except Exception as e:
            print(f"[Workflow] Workflow start failed: {str(e)}")
            error_state = initial_state.copy()
            error_state.update({
                'error': str(e),
                'workflow_complete': True,
                'final_status': 'FAILED'
            })
            return error_state

    def continue_workflow(self, session_id: str, human_input: Any) -> WorkflowState:
        """Continue workflow with human input"""
        try:
            print(f"[Workflow] Continuing workflow for session: {session_id} with input: {human_input}")
            thread_config = {"configurable": {"thread_id": session_id}}
            
            # Resume the workflow with user input using Command
            from langgraph.types import Command
            result = self.workflow.invoke(
                Command(resume=human_input),
                config={**thread_config, "recursion_limit": 100}
            )
            
            return result

        except Exception as e:
            print(f"[Workflow] Workflow continuation failed: {str(e)}")
            return {
                'session_id': session_id,
                'error': str(e),
                'workflow_complete': True,
                'final_status': 'FAILED'
            }

    def get_workflow_state(self, session_id: str) -> WorkflowState:
        """Get current workflow state"""
        try:
            thread_config = {"configurable": {"thread_id": session_id}}
            state = self.workflow.get_state(thread_config)
            
            if state is None:
                return None
            
            return state.values

        except Exception as e:
            print(f"[ERROR] Error getting workflow state for {session_id}: {e}")
            return None