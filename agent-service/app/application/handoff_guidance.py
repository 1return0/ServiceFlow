from __future__ import annotations

from dataclasses import dataclass

from app.domain.triage_plan import HandoffReason


@dataclass(frozen=True)
class HandoffGuidance:
    reason: HandoffReason
    title: str
    message: str
    immediate_actions: tuple[str, ...]


_GUIDANCE_BY_REASON: dict[HandoffReason, HandoffGuidance] = {
    "account_security_risk": HandoffGuidance(
        reason="account_security_risk",
        title="账号安全风险：请停止继续使用当前凭证",
        message="系统不会自动查询或修改个人工单，请通过学校正式服务渠道联系人工人员。",
        immediate_actions=(
            "不要在不可信页面继续输入账号、密码或验证码。",
            "通过学校官方入口尽快修改密码。",
            "联系人工服务人员并说明账号安全风险。",
        ),
    ),
    "physical_safety_risk": HandoffGuidance(
        reason="physical_safety_risk",
        title="设备安全风险：请停止使用相关设备",
        message="系统不会自动执行设备操作或普通工单查询，请由现场人员按学校安全流程处理。",
        immediate_actions=(
            "立即停止使用相关设备，并远离可能存在风险的区域。",
            "如有火情或人身风险，请按学校紧急安全流程联系现场人员。",
            "联系人工服务人员，说明设备与现场情况。",
        ),
    ),
}


def get_handoff_guidance(reason: HandoffReason) -> HandoffGuidance:
    return _GUIDANCE_BY_REASON[reason]
