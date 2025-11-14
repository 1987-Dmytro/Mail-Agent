# Mail Agent Usability Testing Protocol
**Story 4.8: End-to-End Onboarding Testing and Polish**
**Date Created:** 2025-11-14
**Version:** 1.0

## Overview

This document outlines the protocol for conducting usability testing sessions with 3-5 non-technical users to validate the Mail Agent onboarding experience.

**Testing Goals:**
- Measure onboarding completion time (target: <10 minutes per NFR005)
- Measure success rate (target: 90%+ complete successfully per NFR005)
- Identify pain points and areas of confusion
- Validate clarity of instructions and error messages
- Assess overall user satisfaction (SUS score)

## Participant Criteria

**Target Participants: 3-5 non-technical users**

**Inclusion Criteria:**
- German-speaking professionals
- Active Gmail user (personal or work email)
- Active Telegram user
- No prior experience with Mail Agent
- Age range: 25-55 years
- Mix of technical comfort levels (beginner to intermediate)

**Exclusion Criteria:**
- Developers or UX designers
- Anyone with prior knowledge of Mail Agent
- Users without both Gmail and Telegram accounts

## Pre-Test Setup (5 minutes)

### Facilitator Preparation

1. **Environment Setup**
   - Open Mail Agent in production/staging environment
   - Start screen recording software (OBS, QuickTime, Zoom)
   - Open observation checklist document
   - Prepare timer/stopwatch
   - Have participant consent form ready

2. **Participant Welcome**
   - Introduce yourself and thank participant for their time
   - Explain the purpose: testing the product, not testing them
   - Emphasize there are no wrong answers
   - Reassure that feedback (positive or negative) is valuable

3. **Consent and Recording**
   - Present and review consent form
   - Explain screen recording and data usage
   - Obtain signed consent (digital or physical)
   - Start screen recording

4. **Think-Aloud Protocol Explanation**
   - Explain think-aloud method: "Please verbalize your thoughts as you go"
   - Example: "I'm looking for... I'm clicking this because..."
   - Emphasize it's okay to express confusion, frustration, or uncertainty
   - Practice with a simple task (e.g., "Find the search button on Google")

5. **Gmail and Telegram Verification**
   - Confirm participant has Gmail account credentials ready
   - Confirm participant has Telegram installed on phone
   - Verify internet connection is stable

## Main Testing Session (10-15 minutes)

### Task 1: Complete Mail Agent Setup

**Instructions to Participant:**

> "Imagine you've just heard about Mail Agent, a service that helps organize your Gmail inbox using Telegram notifications. Your goal is to set up the service from start to finish. Please complete the entire setup process as you would if I weren't here. Remember to think aloud as you go."

**Observer Actions:**
- **Do NOT intervene** unless participant is stuck for >3 minutes
- Take detailed notes on observation checklist
- Record timestamps for each major step
- Note any hesitations, confusion, or errors
- Observe facial expressions and body language

### Step-by-Step Observations

**Step 1: Gmail OAuth Connection**
- [ ] Participant finds "Connect Gmail" button easily
- [ ] Participant understands permission requirements
- [ ] OAuth flow completes successfully
- [ ] Participant recognizes success state
- Time spent: _____ minutes
- Confusion points: _____________________

**Step 2: Telegram Bot Linking**
- [ ] Participant understands how to find Mail Agent bot
- [ ] Participant copies linking code successfully
- [ ] Participant sends code to bot in Telegram
- [ ] Participant returns to web interface
- [ ] Verification completes successfully
- Time spent: _____ minutes
- Confusion points: _____________________

**Step 3: Folder Configuration**
- [ ] Participant understands folder concept
- [ ] Participant creates at least one folder
- [ ] Participant enters keywords appropriately
- [ ] Participant uses color picker (if attempted)
- [ ] Participant proceeds to next step
- Time spent: _____ minutes
- Confusion points: _____________________

**Step 4: Notification Preferences**
- [ ] Participant understands batch vs. immediate notifications
- [ ] Participant configures quiet hours correctly
- [ ] Participant uses "Test Notification" (if attempted)
- [ ] Participant completes setup successfully
- Time spent: _____ minutes
- Confusion points: _____________________

### Task 2: Additional Exploration (Optional, if time permits)

**Instructions to Participant:**

> "Now that setup is complete, please explore the dashboard and settings. Try to find where you would change your folder categories or notification preferences."

**Observations:**
- Can participant navigate to folder settings?
- Can participant navigate to notification settings?
- Does dashboard information make sense to participant?

## Post-Test Interview (5-10 minutes)

### Open-Ended Questions

1. **Overall Experience**
   - "How would you describe your experience setting up Mail Agent?"
   - "Was the setup process easier or harder than you expected?"

2. **Pain Points**
   - "What was the most confusing or frustrating part of the setup?"
   - "Was there any point where you didn't know what to do next?"
   - "Were there any error messages or instructions that were unclear?"

3. **Success Factors**
   - "What part of the setup went most smoothly?"
   - "What helped you understand what to do?"

4. **Comparison**
   - "Have you used similar services before? How does this compare?"
   - "Would you continue using this service after setup?"

5. **Improvements**
   - "If you could change one thing about the setup, what would it be?"
   - "What additional help or guidance would have been useful?"

6. **Recommendation**
   - "Would you recommend this service to a colleague? Why or why not?"

### System Usability Scale (SUS) Questionnaire

Rate each statement from 1 (Strongly Disagree) to 5 (Strongly Agree):

1. I think that I would like to use this system frequently
2. I found the system unnecessarily complex
3. I thought the system was easy to use
4. I think that I would need the support of a technical person to be able to use this system
5. I found the various functions in this system were well integrated
6. I thought there was too much inconsistency in this system
7. I would imagine that most people would learn to use this system very quickly
8. I found the system very cumbersome to use
9. I felt very confident using the system
10. I needed to learn a lot of things before I could get going with this system

**SUS Score Calculation:**
- For odd items (1, 3, 5, 7, 9): Subtract 1 from user response
- For even items (2, 4, 6, 8, 10): Subtract user response from 5
- Sum all values and multiply by 2.5
- Result: 0-100 score (68+ is above average, 80+ is excellent)

## Closing (2 minutes)

1. **Thank Participant**
   - Express sincere gratitude for their time and feedback
   - Explain how their feedback will improve the product

2. **Compensation** (if applicable)
   - Provide gift card, payment, or other compensation
   - Collect receipt or signature if required

3. **Follow-up**
   - Ask if they'd like to be contacted for future testing
   - Provide contact information if they have questions

4. **Stop Recording**
   - Save screen recording with participant ID (anonymized)
   - Save all notes and checklist data

## Data Recording

For each participant, record:

- **Participant ID:** (anonymized, e.g., P001, P002)
- **Date & Time:**
- **Total Onboarding Time:** _____ minutes _____ seconds
- **Completion Status:** ✓ Successful / ✗ Failed
- **Step-by-Step Times:** Gmail ___ | Telegram ___ | Folders ___ | Preferences ___
- **SUS Score:** _____ / 100
- **Key Pain Points:** (brief bullet points)
- **Key Positive Feedback:** (brief bullet points)
- **Notable Quotes:** (direct quotes with context)

## Success Metrics

**Primary KPIs (from NFR005):**
- Onboarding completion rate: **Target ≥90%**
- Average onboarding time: **Target <10 minutes**

**Secondary KPIs:**
- SUS Score: **Target ≥70 (Good to Excellent)**
- Critical issues (blocking completion): **Target 0**
- Major issues (causing confusion/delay): **Target <5**

## Next Steps After Testing

1. Compile all participant data into results report
2. Categorize issues by severity (critical, major, minor)
3. Create prioritized fix list for Task 3 (Polish and Refinement)
4. Calculate aggregate metrics (completion rate, avg time, SUS score)
5. Extract key insights and recommendations
6. Share findings with team for implementation

---

**Protocol Version:** 1.0
**Last Updated:** 2025-11-14
**Approved By:** Epic 4 Team
