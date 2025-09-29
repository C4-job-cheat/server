from rest_framework import serializers


class InterviewHistoryRequestSerializer(serializers.Serializer):
    """면접 기록 조회 요청 시리얼라이저."""
    persona_id = serializers.CharField(max_length=100, help_text="페르소나 ID")


class InterviewSessionSummarySerializer(serializers.Serializer):
    """면접 세션 요약 시리얼라이저."""
    interview_session_id = serializers.CharField(help_text="면접 세션 ID")
    score = serializers.FloatField(help_text="점수")
    grade = serializers.CharField(help_text="등급")
    total_time = serializers.IntegerField(help_text="총 소요 시간 (초)")
    created_at = serializers.DateTimeField(help_text="생성일시")
    completed_at = serializers.DateTimeField(help_text="완료일시")


class InterviewHistoryResponseSerializer(serializers.Serializer):
    """면접 기록 조회 응답 시리얼라이저."""
    total_sessions = serializers.IntegerField(help_text="총 면접 횟수")
    average_score = serializers.FloatField(help_text="평균 점수")
    highest_score = serializers.FloatField(help_text="최고 점수")
    total_practice_time = serializers.IntegerField(help_text="총 연습 시간 (초)")
    sessions = InterviewSessionSummarySerializer(many=True, help_text="면접 세션 목록")
    persona_card = serializers.DictField(help_text="페르소나 카드 정보")


class InterviewPreparationRequestSerializer(serializers.Serializer):
    """면접 준비 데이터 요청 시리얼라이저."""
    persona_id = serializers.CharField(max_length=100, help_text="페르소나 ID")


class InterviewPreparationResponseSerializer(serializers.Serializer):
    """면접 준비 데이터 응답 시리얼라이저."""
    persona_card = serializers.DictField(help_text="페르소나 카드 데이터")
    cover_letters = serializers.ListField(
        child=serializers.DictField(),
        help_text="자기소개서 목록"
    )


class CoverLetterSummarySerializer(serializers.Serializer):
    """자기소개서 요약 시리얼라이저."""
    id = serializers.CharField(help_text="자기소개서 ID")
    company_name = serializers.CharField(help_text="지원 회사 이름")
    created_at = serializers.DateTimeField(help_text="생성일시")
    character_count = serializers.IntegerField(help_text="글자 수")
    style = serializers.CharField(help_text="자기소개서 스타일")


class InterviewQuestionGenerationRequestSerializer(serializers.Serializer):
    """면접 질문 생성 요청 시리얼라이저."""
    persona_id = serializers.CharField(max_length=100, help_text="페르소나 ID")
    cover_letter_id = serializers.CharField(
        max_length=100, 
        required=False, 
        allow_blank=True,
        help_text="자기소개서 ID (선택사항)"
    )
    use_voice = serializers.BooleanField(
        default=False,
        help_text="음성 면접 여부"
    )


class QuestionSerializer(serializers.Serializer):
    """질문 시리얼라이저."""
    question_id = serializers.CharField(help_text="질문 ID")
    question_number = serializers.IntegerField(help_text="질문 번호")
    question_type = serializers.CharField(help_text="질문 유형")
    question_text = serializers.CharField(help_text="질문 내용")


class InterviewQuestionGenerationResponseSerializer(serializers.Serializer):
    """면접 질문 생성 응답 시리얼라이저."""
    interview_session_id = serializers.CharField(help_text="면접 세션 ID")
    question = QuestionSerializer(help_text="첫 번째 질문")


class AnswerSubmissionRequestSerializer(serializers.Serializer):
    """답변 제출 요청 시리얼라이저."""
    persona_id = serializers.CharField(max_length=100, help_text="페르소나 ID")
    interview_session_id = serializers.CharField(max_length=100, help_text="면접 세션 ID")
    question_id = serializers.CharField(max_length=100, help_text="질문 ID")
    question_number = serializers.IntegerField(help_text="질문 번호")
    answer_text = serializers.CharField(help_text="답변 내용")
    time_taken = serializers.IntegerField(help_text="답변 소요 시간 (초)")


class VoiceAnswerSubmissionRequestSerializer(serializers.Serializer):
    """음성 답변 제출 요청 시리얼라이저."""
    persona_id = serializers.CharField(max_length=100, help_text="페르소나 ID")
    interview_session_id = serializers.CharField(max_length=100, help_text="면접 세션 ID")
    question_id = serializers.CharField(max_length=100, help_text="질문 ID")
    question_number = serializers.IntegerField(help_text="질문 번호")
    audio_file = serializers.FileField(help_text="음성 파일 (WebM 형식)")
    time_taken = serializers.IntegerField(help_text="답변 소요 시간 (초)")


class EvaluationSerializer(serializers.Serializer):
    """평가 시리얼라이저."""
    good_points = serializers.ListField(
        child=serializers.CharField(),
        help_text="잘한 점 목록"
    )
    improvement_points = serializers.ListField(
        child=serializers.CharField(),
        help_text="개선할 점 목록"
    )
    sample_answer = serializers.CharField(help_text="모범 답변 예시")
    question_intent = serializers.ListField(
        child=serializers.CharField(),
        help_text="질문의 의도 목록"
    )
    question_score = serializers.IntegerField(help_text="질문 점수")




class NextQuestionResponseSerializer(serializers.Serializer):
    """다음 질문 응답 시리얼라이저."""
    question_id = serializers.CharField(help_text="질문 ID")
    question_number = serializers.IntegerField(help_text="질문 번호")
    question_type = serializers.CharField(help_text="질문 유형")
    question_text = serializers.CharField(help_text="질문 내용")


class QuestionResultSerializer(serializers.Serializer):
    """질문 결과 시리얼라이저."""
    question_id = serializers.CharField(help_text="질문 ID")
    question_number = serializers.IntegerField(help_text="질문 번호")
    question_type = serializers.CharField(help_text="질문 유형")
    question_text = serializers.CharField(help_text="질문 내용")
    answer_text = serializers.CharField(help_text="답변 내용")
    time_taken = serializers.IntegerField(help_text="답변 소요 시간")


class InterviewSessionResultSerializer(serializers.Serializer):
    """면접 세션 결과 시리얼라이저."""
    interview_session_id = serializers.CharField(help_text="면접 세션 ID")
    user_id = serializers.CharField(help_text="사용자 ID")
    persona_id = serializers.CharField(help_text="페르소나 ID")
    total_questions = serializers.IntegerField(help_text="총 질문 수")
    total_time = serializers.IntegerField(help_text="총 소요 시간")
    average_answer_time = serializers.FloatField(help_text="평균 답변 시간")
    total_answers = serializers.IntegerField(help_text="총 답변 수")
    average_answer_length = serializers.FloatField(help_text="평균 답변 길이")
    score = serializers.FloatField(help_text="총점")
    grade = serializers.CharField(help_text="등급")
    status = serializers.CharField(help_text="상태")
    use_voice = serializers.BooleanField(help_text="음성 면접 여부")
    questions = QuestionResultSerializer(many=True, help_text="질문 목록")
    final_good_points = serializers.ListField(
        child=serializers.CharField(),
        help_text="최종 잘한 점 목록"
    )
    final_improvement_points = serializers.ListField(
        child=serializers.CharField(),
        help_text="최종 개선할 점 목록"
    )
    created_at = serializers.DateTimeField(help_text="생성일시")
    updated_at = serializers.DateTimeField(help_text="수정일시")
    completed_at = serializers.DateTimeField(help_text="완료일시")


class QuestionDetailResponseSerializer(serializers.Serializer):
    """질문 상세 응답 시리얼라이저."""
    question_id = serializers.CharField(help_text="질문 ID")
    question_number = serializers.IntegerField(help_text="질문 번호")
    question_type = serializers.CharField(help_text="질문 유형")
    question_text = serializers.CharField(help_text="질문 내용")
    answer_text = serializers.CharField(help_text="답변 내용")
    answer_length = serializers.IntegerField(help_text="답변 길이")
    time_taken = serializers.IntegerField(help_text="답변 소요 시간")
    is_answered = serializers.BooleanField(help_text="답변 여부")
    question_score = serializers.IntegerField(help_text="질문 점수")
    good_points = serializers.ListField(
        child=serializers.CharField(),
        help_text="잘한 점 목록"
    )
    improvement_points = serializers.ListField(
        child=serializers.CharField(),
        help_text="개선할 점 목록"
    )
    sample_answer = serializers.CharField(help_text="모범 답변 예시")
    question_intent = serializers.ListField(
        child=serializers.CharField(),
        help_text="질문의 의도 목록"
    )
    created_at = serializers.DateTimeField(help_text="생성일시")
    updated_at = serializers.DateTimeField(help_text="수정일시")