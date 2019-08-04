import json
import os

output = {}
data = {
  "agent_name": "my_AL_agent",
  "agent_type": "ModularAgent",
  "stay_active": True,
  "dont_save": True,
  "no_ops_parse": True,
  "args": {
    "when_learner": "trestle",
    "where_learner": "MostSpecific"
  },
  "feature_set": [
    "equals"
  ],
  "function_set": [
    "add",
    "subtract",
    "multiply",
    "divide"
  ],
  "set_params": {
        "HTML": "ExponentsOperation.html",
        "examples_only": False
    },
  "repetitions" : 1,
  "outer_loop_controller" : "BKTKCsExponentSingle",
}

problem_set = []
fileList = os.listdir(os.getcwd() +"/MassProduction/")

for f in fileList:
	dic = {}
	str = "/MassProduction/" + f
	dic["question_file"] = str
	
	KCList = []
	KC = f[:2]
	KCList.append(KC)
	dic["kc_list"] = KCList

	problem_set.append(dic)

data["problem_set"] = problem_set
output["training_set1"] = [data]

with open("outer_loop_single_kcs.json", "w") as write_file:
	json.dump(output, write_file, indent = 4)