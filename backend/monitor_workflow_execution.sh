#!/bin/bash
# Monitor workflow execution logs in real-time
# This helps verify that the workflow executes correctly when testing with a real email

echo "==================================================================="
echo "WORKFLOW EXECUTION MONITOR"
echo "==================================================================="
echo ""
echo "Monitoring logs for workflow execution..."
echo "Looking for these key events:"
echo "  1. Email received and persisted"
echo "  2. Workflow started"
echo "  3. Sorting proposal sent to Telegram"
echo "  4. User approves sorting"
echo "  5. Draft generated (if needs_response)"
echo "  6. Draft notification sent to Telegram (if needs_response)"
echo "  7. User clicks Send/Reject"
echo "  8. send_email_response node executes (if Send clicked)"
echo "  9. execute_action node executes"
echo "  10. send_confirmation node executes"
echo "  11. Messages deleted"
echo "  12. Summary sent"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo "==================================================================="
echo ""

cd "/Users/hdv_1987/Desktop/Прроекты/Mail Agent"

# Monitor celery and backend logs for workflow events
docker-compose logs -f --tail=0 celery-worker backend 2>&1 | grep --line-buffered -E \
    "email_persisted|workflow_started|telegram_message.*sent|callback_.*_processing|callback_resuming_workflow|node_send_email_response_start|node_execute_action_start|send_confirmation_start|deleted_.*_message|send_confirmation_summary_sent|draft_decision|user_decision" \
    | while read line; do
        # Color code different events
        if [[ $line == *"email_persisted"* ]]; then
            echo -e "\033[0;32m[1. EMAIL RECEIVED]\033[0m $line"
        elif [[ $line == *"workflow_started"* ]]; then
            echo -e "\033[0;32m[2. WORKFLOW STARTED]\033[0m $line"
        elif [[ $line == *"sorting_proposal_telegram_sent"* ]]; then
            echo -e "\033[0;33m[3. SORTING PROPOSAL SENT]\033[0m $line"
        elif [[ $line == *"callback_approve_processing"* ]]; then
            echo -e "\033[0;34m[4. USER APPROVED SORTING]\033[0m $line"
        elif [[ $line == *"draft_generated"* ]]; then
            echo -e "\033[0;32m[5. DRAFT GENERATED]\033[0m $line"
        elif [[ $line == *"draft_telegram_sent"* ]]; then
            echo -e "\033[0;33m[6. DRAFT NOTIFICATION SENT]\033[0m $line"
        elif [[ $line == *"callback_send_response_processing"* ]]; then
            echo -e "\033[0;34m[7. USER CLICKED SEND]\033[0m $line"
        elif [[ $line == *"callback_reject_response_processing"* ]]; then
            echo -e "\033[0;34m[7. USER CLICKED REJECT]\033[0m $line"
        elif [[ $line == *"callback_resuming_workflow"* ]]; then
            echo -e "\033[0;35m[WORKFLOW RESUMING]\033[0m $line"
        elif [[ $line == *"node_send_email_response_start"* ]]; then
            echo -e "\033[0;32m[8. SENDING EMAIL]\033[0m $line"
        elif [[ $line == *"node_execute_action_start"* ]]; then
            echo -e "\033[0;32m[9. EXECUTING ACTION]\033[0m $line"
        elif [[ $line == *"send_confirmation_start"* ]]; then
            echo -e "\033[0;32m[10. SENDING CONFIRMATION]\033[0m $line"
        elif [[ $line == *"deleted_sorting_proposal_message"* ]]; then
            echo -e "\033[0;36m[11. DELETED SORTING PROPOSAL]\033[0m $line"
        elif [[ $line == *"deleted_draft_notification_message"* ]]; then
            echo -e "\033[0;36m[11. DELETED DRAFT NOTIFICATION]\033[0m $line"
        elif [[ $line == *"send_confirmation_summary_sent"* ]]; then
            echo -e "\033[0;32m[12. SUMMARY SENT]\033[0m ✅ WORKFLOW COMPLETE!"
            echo ""
        else
            echo "$line"
        fi
    done
