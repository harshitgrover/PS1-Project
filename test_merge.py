from src.agents.constraints.constraint_agent import ConstraintAgent
from src.agents.constraints.validator import ConstraintValidationError
from dotenv import load_dotenv

load_dotenv()
agent = ConstraintAgent(entity_engine_url="http://localhost:8001")
try:
    res = agent.process_zoning_input({}, user_text="I want 3 bedrooms and 2 bathrooms")
    print("SUCCESS: ", list(res["Properties"]["interior"]["room_specs"].keys()))
except ConstraintValidationError as e:
    print("FAILED with:")
    print(getattr(e, "reasons", [str(e)]))
