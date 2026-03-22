import sys
import re
import os

script_dir = r"c:\Users\mehta\Desktop\New folder\LEVI-AI"
sys.path.append(script_dir)
import learning_routes

main_file = os.path.join(script_dir, "backend", "main.py")

with open(main_file, "r", encoding="utf-8") as f:
    code = f.read()

# Replace chat route
chat_pattern = re.compile(r'@app\.post\("/chat"\).*?(?=\n@app\.get\("/export_my_data"\))', re.DOTALL)
new_routes = learning_routes.UPDATED_CHAT_ROUTE.strip() + "\n\n" + learning_routes.LEARNING_ROUTES.strip()
code = chat_pattern.sub(new_routes, code)

# Update imports
import_str1 = """    from backend.learning import (
        collect_training_sample, UserPreferenceModel,
        AdaptivePromptManager, get_learning_stats, infer_implicit_feedback
    )
    from backend.trainer import trigger_training_pipeline, get_model_history, get_active_model_id, generate_with_active_model
    from backend.training_models import TrainingData, ResponseFeedback, ModelVersion, TrainingJob"""

import_str2 = """        from learning import (
            collect_training_sample, UserPreferenceModel,
            AdaptivePromptManager, get_learning_stats, infer_implicit_feedback
        )
        from trainer import trigger_training_pipeline, get_model_history, get_active_model_id, generate_with_active_model
        from training_models import TrainingData, ResponseFeedback, ModelVersion, TrainingJob"""

if "from backend.learning import" not in code:
    code = code.replace("    from backend.tasks import generate_video_task as generate_video_async", "    from backend.tasks import generate_video_task as generate_video_async\n" + import_str1)
if "from learning import" not in code.split("except (ImportError, ModuleNotFoundError) as e2:")[0]:
    code = code.replace("        from tasks import generate_video_task as generate_video_async", "        from tasks import generate_video_task as generate_video_async\n" + import_str2)

with open(main_file, "w", encoding="utf-8") as f:
    f.write(code)

print("main.py updated successfully.")
