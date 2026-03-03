from rest_framework import serializers
from .models import Proposal, Ambiguity, Discrepancy


class AmbiguitySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Ambiguity
        fields = ["id", "ambiguity_proposal_data", "ambiguity_response", "created_at"]
        read_only_fields = ["created_at"]


class DiscrepancySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Discrepancy
        fields = ["id", "discrepancy_proposal_data", "discrepancy_response", "created_at"]
        read_only_fields = ["created_at"]


class ProposalSerializer(serializers.ModelSerializer):
    ambiguities = AmbiguitySerializer(many=True, required=False)
    discrepancies = DiscrepancySerializer(many=True, required=False)

    class Meta:
        model = Proposal
        fields = [
            "id",
            "age",
            "gender",
            "proposal_data",
            "response_data",
            "underwriting_decision",
            "identified_health_profile",
            "decision_rationale",
            "waiting_period_details",
            "refer_to_uwr_details",
            "more_questions_details",
            "ambiguities",
            "discrepancies",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate_age(self, value):
        if value < 0 or value > 120:
            raise serializers.ValidationError("Enter a valid age.")
        return value

    def create(self, validated_data):
        ambiguities_data = validated_data.pop("ambiguities", [])
        discrepancies_data = validated_data.pop("discrepancies", [])

        proposal = Proposal.objects.create(**validated_data)

        # create related ambiguities
        for amb in ambiguities_data:
            Ambiguity.objects.create(proposal=proposal, **amb)

        # create related discrepancies
        for disc in discrepancies_data:
            Discrepancy.objects.create(proposal=proposal, **disc)

        return proposal

    def update(self, instance, validated_data):
        ambiguities_data = validated_data.pop("ambiguities", None)
        discrepancies_data = validated_data.pop("discrepancies", None)

        # update simple fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If ambiguities provided, perform a simple sync strategy:
        # - If item has id -> update
        # - Else -> create
        # - Items not present in payload are left unchanged (or you can delete them if desired)
        if ambiguities_data is not None:
            for amb in ambiguities_data:
                amb_id = amb.get("id", None)
                if amb_id:
                    try:
                        obj = Ambiguity.objects.get(pk=amb_id, proposal=instance)
                        for k, v in amb.items():
                            if k != "id":
                                setattr(obj, k, v)
                        obj.save()
                    except Ambiguity.DoesNotExist:
                        Ambiguity.objects.create(proposal=instance, **amb)
                else:
                    Ambiguity.objects.create(proposal=instance, **amb)

        if discrepancies_data is not None:
            for disc in discrepancies_data:
                disc_id = disc.get("id", None)
                if disc_id:
                    try:
                        obj = Discrepancy.objects.get(pk=disc_id, proposal=instance)
                        for k, v in disc.items():
                            if k != "id":
                                setattr(obj, k, v)
                        obj.save()
                    except Discrepancy.DoesNotExist:
                        Discrepancy.objects.create(proposal=instance, **disc)
                else:
                    Discrepancy.objects.create(proposal=instance, **disc)

        return instance
    
    
# serializers.py
from rest_framework import serializers
from .models import Uwquestions

class UwquestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Uwquestions
        fields = [
            "id",
            "proposal",       # foreign key reference
            "answers",        # JSONField
            "created_at",     # timestamp
        ]
        read_only_fields = ["id", "created_at"]