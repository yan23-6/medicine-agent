"""The product's constrained top-level agent, independent of any coding host."""
from medicine_agent.analysis.documents import capabilities
from medicine_agent.analysis.models import AnalysisError, AnalysisRequest
from medicine_agent.analysis.service import DataAnalysisAgent
from medicine_agent.domain.owned_analysis import OwnedAnalysisRequest
from medicine_agent.analysis.file_learning import FileLearningService
from medicine_agent.analysis.catalog import PackageCatalog


class OrchestratorAgent:
    def __init__(self, workspace, package_root=None, model_client=None):
        self.files = FileLearningService(workspace,package_root,model_client)
        self.workspace,self.model_client=workspace,model_client

    @property
    def data_agent(self):
        """Legacy internal directory interface, retained for old callers/checkpoints."""
        return DataAnalysisAgent(self.workspace,self.files.library.root,self.model_client)

    def receive(self, goal: str, payload: dict):
        if goal == "analyze_files":
            return self.files.submit(payload)
        if goal == "query_knowledge":
            from pydantic import ValidationError
            from medicine_agent.domain.retrieval import LocalKnowledgeQuery
            try:
                payload=LocalKnowledgeQuery.model_validate(payload).model_dump(mode='json',exclude_none=True)
            except ValidationError as exc:
                raise AnalysisError("QUERY_INVALID", "Provide a supported knowledge query") from exc
            if not list(self.files.library.root.glob('*.medpkg')) and list(self.files.library.root.rglob('manifest.json')):
                return self.data_agent.catalog.query(self.data_agent.facade,**payload)
            return self.files.query(**payload)
        if goal == 'revise_candidate':
            # Explicit review IDs route to deterministic persistence, never an LLM.
            if list(self.files.library.root.glob('*.medpkg')):
                return self.files.revise(payload)
            return PackageCatalog(self.files.library.root).revise_candidate(payload)
        if goal=='record_review':return self.files.record_review(payload)
        if goal=='review_queue':return self.files.review_queue(payload.get('scope','node'))
        if goal == "capabilities":
            return {"documents": capabilities(), "goals": ["analyze_files", "query_knowledge", 'revise_candidate','record_review','review_queue'],
                    'package_format':'.medpkg','package_folder':str(self.files.library.root),
                    "consultation": "not_implemented"}
        raise AnalysisError("AGENT_CAPABILITY_MISSING", "The product has no implemented handler for this goal")

    def execute(self, parent_task_id, **limits):
        if parent_task_id.startswith('learning_'):
            return self.files.run(parent_task_id,**limits)
        task = self.data_agent.store.get(parent_task_id)
        if task["parent"] is not None:
            raise AnalysisError("ORCHESTRATION_TASK_REQUIRED", "Use the parent task identity")
        return self.data_agent.run(parent_task_id, **limits)
