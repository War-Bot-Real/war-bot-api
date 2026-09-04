from api.models.Nation import Nation
from api.models.Operation import Operation

def collectIncome(nation):
    return {
        nation["Name"]: {
            "Balance": Operation('add', 10000)
        }
    }