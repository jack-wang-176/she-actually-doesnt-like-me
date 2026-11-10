#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/nodes/solace_node.py
分布式节点 4：复杂情境心理抚慰与主体性重建节点 (SolaceRebuilderNode)
核心目的：当单人分析识别出“假性亲密、广谱养鱼、间歇性强化、借口去酒吧合群、回避陪伴需求”等复杂内耗局面时，
拒绝冷冰冰的说教或廉价心灵鸡汤，而是提供有理有据、接住用户情绪的深度安慰，并引导其将能量转回高确定性的个人发展主线。
输出：state/solace_state.json
"""

import json
from pathlib import Path


def run_solace_node(state_dir: Path, personal_mainline: str = "核心技术研发与个人硬核成长主线") -> dict:
    state_dir = Path(state_dir)
    quant = json.loads((state_dir / "quant_state.json").read_text(encoding="utf-8"))
    defilter = json.loads((state_dir / "defilter_state.json").read_text(encoding="utf-8"))
    jev = json.loads((state_dir / "jev_state.json").read_text(encoding="utf-8"))

    verdict = jev["decision"]["verdict_code"]
    pathologies = defilter["detected_pathologies"]
    need_deep_solace = (verdict == "STOP_AND_PIVOT" or len(pathologies) >= 2)

    if need_deep_solace:
        empathy_opening = (
            "先给自己松绑：你在这段关系里感到的恶心、委屈、掏空与推进无力，绝不是因为你『不够好』或『太敏感』。"
            "恰恰相反，你是一个极其真诚、重诺且愿意实质付出的人——当你用排他性的真心与真金白银的资源，去碰撞一个"
            "把热情当廉价社交货币、在公开场合避嫌、甚至用『很多人喜欢我随便选』来炫耀筹码的人时，你的本能厌恶是你身体最忠诚的防线在保护你。"
        )
        cognitive_reframe = [
            "1. 【为你的直觉正名】：当初听到她炫耀备胎池时的生理性不适、以及发现她拿借口掩饰去酒吧合群时的下头感，说明你的潜意识早就看穿了真相。你中间的反复，只是因为善良的人很难立刻接受『对方其实极其功利与敷衍』的落差。",
            "2. 【剥离『认真回长文』的伪善滤镜】：她在你最需要陪伴时回的那一大段『把情绪跟生活分开、规律作息、暂时先不讨论』，不是深情，而是零成本的免责声明。给你几句居高临下的生活建议不需要付出任何代价，却能心安理得地继续享受你的资源与捧场。",
            "3. 【承认沉没成本，但拒绝继续失血】：过去投入的 2 万多字、近八成的主动破冰和资源支持，证明了你拥有极强的爱人与行动的能力；只是这一次投错了标的。看清『在这段关系里什么都没得到』不是失败，而是彻底止损、拿回人生主导权的觉醒时刻。"
        ]
        rebuilding_protocol = {
            "target_mainline": personal_mainline,
            "principle": "用 100% 确定性的硬核创造，接管不可控的低维社交内耗",
            "steps": [
                "【彻底静音与零破冰】：不质问、不翻旧账、不删好友演戏，直接将主动发起率降为 0%，在心里将其归档为『已结项的无效样本』。",
                f"【能量锚点强制迁移】：每当深夜产生倾诉惯性或回想细节时，立刻把注意力切换到『{personal_mainline}』的具体工程任务上——代码、芯片架构与技术突破不会对你忽冷忽热，你付出的每一小时都会沉淀为谁也拿不走的硬实力。",
                "【重构择偶准入底线】：未来的关系里，凡是出现『公开场合避嫌』『炫耀追求者数量』『隐瞒夜场行踪』『回避真实陪伴诉求』中任何一条，直接一票否决，把真心留给同频、坦诚且双向奔赴的人。"
            ]
        }
    else:
        empathy_opening = (
            "当前互动整体处于可控区间。保持平视、自在的节奏，既不自我矮化讨好，也不过度防御，始终以自己的核心生活与成长节奏为圆心。"
        )
        cognitive_reframe = [
            "1. 【线上热度只是敲门砖】：保持字数与破冰频率的双向平衡，把更多判断权重放在线下真实相处时的自然度与排他感上。",
            "2. 【主体性优先】：无论关系处于哪个阶段，个人的核心事业与身心秩序永远排在第一位。"
        ]
        rebuilding_protocol = {
            "target_mainline": personal_mainline,
            "principle": "以稳固的个人成长为底座，自然吸引同频伴侣",
            "steps": [
                f"保持 70% 精力聚焦于『{personal_mainline}』，30% 精力用于轻松高质量的线下互动验证。"
            ]
        }

    solace_state = {
        "schema_version": "1.0",
        "node_id": quant["node_id"],
        "node_hash": quant["node_hash"],
        "need_deep_solace": need_deep_solace,
        "empathy_opening": empathy_opening,
        "cognitive_reframe": cognitive_reframe,
        "rebuilding_protocol": rebuilding_protocol,
    }

    (state_dir / "solace_state.json").write_text(json.dumps(solace_state, ensure_ascii=False, indent=2), encoding="utf-8")
    return solace_state
