# -*- coding: utf-8 -*-

import six
import datetime

from flask import abort, current_app, render_template
from flask_login import current_user

from dmapiclient.audit import AuditTypes
from dmutils.email import send_email, EmailError


def get_brief(data_api_client, brief_id, allowed_statuses=None):
    if allowed_statuses is None:
        allowed_statuses = []

    brief = data_api_client.get_brief(brief_id)['briefs']

    if allowed_statuses and brief['status'] not in allowed_statuses:
        abort(404)

    return brief


def is_supplier_selected_for_brief(data_api_client, current_user, brief):
    def domain(email):
        return email.split('@')[-1]

    current_user_domain = domain(current_user.email_address) \
        if domain(current_user.email_address) not in current_app.config.get('GENERIC_EMAIL_DOMAINS') \
        else None
    if brief.get('lot', '') == 'rfx':
        if (hasattr(current_user, 'role') and
           current_user.role == 'supplier' and
           str(current_user.supplier_code) in brief.get('sellers', {}).keys()):
            return True
        else:
            return False
    if brief.get('sellerSelector', '') == 'allSellers':
        return True
    if brief.get('sellerSelector', '') == 'someSellers':
        seller_domain_list = [domain(x).lower() for x in brief.get('sellerEmailList', [])]
        return (current_user.email_address in
                (email_address.lower() for email_address in brief.get('sellerEmailList', [])) or
                (current_user_domain.lower() in seller_domain_list if current_user_domain else False))
    if brief.get('sellerSelector', '') == 'oneSeller':
        return (current_user.email_address.lower() == brief.get('sellerEmail', '').lower() or
                (current_user_domain.lower() == domain(brief.get('sellerEmail', '').lower())
                if current_user_domain else False))
    return False


def is_supplier_not_eligible_for_brief(data_api_client, supplier_code, brief):
    supplier = data_api_client.get_supplier(supplier_code)['supplier']
    # if framework is new framework dm, old or new seller is deemed to be approved
    digital_marketplace_seller = False

    digital_marketplace_framework = data_api_client.get_framework('digital-marketplace')

    for framework in supplier.get('frameworks', []):
        if framework['framework_id'] == digital_marketplace_framework['frameworks']['id']:
            digital_marketplace_seller = True
    existing_seller = len(supplier.get('domains', {'legacy': []})['legacy']) > 0
    old_panel = brief.get('frameworkFramework') == 'dsp'

    if supplier:
        # old panel brief and new seller
        if old_panel and not existing_seller:
            return 'briefs/cant_apply_to_old_panel_opportunity.html'

        # new panel brief and old seller
        if not digital_marketplace_seller and not old_panel:
            return 'briefs/cant_apply_to_new_panel_opportunity.html'

    brief_closing_date = brief.get('dates').get('closing_date')
    application_status = None
    application_id = current_user.application_id
    if application_id:
        try:
            application = data_api_client.get_application(application_id)
            application_type = application.get('application').get('type')
            if application_type == 'new' or application_type == 'upgrade':
                application_status = application.get('application').get('status')
        except:  # noqa
            pass

    # user expresses interest in brief but they are not an assessed seller
    if application_status == 'submitted':
        # triggers jiraapi fn to prioritise a related approval task
        data_api_client.req.prioritise(application_id).post(brief_closing_date)
        return 'briefs/pending_initial_seller_assessment.html'

    # sanity check
    if supplier is None:
        return 'briefs/not_is_supplier_eligible_for_brief_error.html'


def supplier_has_a_brief_response(data_api_client, supplier_code, brief_id):
    brief_response_result = data_api_client.find_brief_responses(brief_id=brief_id, supplier_code=supplier_code)
    brief_responses = brief_response_result['briefResponses']
    return len(brief_responses) != 0


def supplier_is_assessed(supplier, domain):
    return 'assessed' in supplier['supplier']['domains'] and \
        domain in supplier['supplier']['domains']['assessed']


def supplier_is_unassessed(supplier, domain):
    return 'unassessed' in supplier['supplier']['domains'] and \
        domain in supplier['supplier']['domains']['unassessed']


def send_brief_clarification_question(data_api_client, brief, clarification_question):
    # Email the question to brief owners
    email_body = render_template(
        "emails/brief_clarification_question.html",
        brief_id=brief['id'],
        brief_name=brief['title'],
        publish_by_date=brief['clarificationQuestionsPublishedBy'],
        framework_slug=brief['frameworkSlug'],
        lot_slug=brief['lotSlug'],
        message=clarification_question,
    )
    try:
        send_email(
            to_email_addresses=get_brief_user_emails(brief),
            email_body=email_body,
            subject=u"You’ve received a new supplier question about ‘{}’".format(brief['title']),
            from_email=current_app.config['CLARIFICATION_EMAIL_FROM'],
            from_name="{} Supplier".format(brief['frameworkName'])
        )
    except EmailError as e:
        current_app.logger.error(
            "Brief question email failed to send. error={error} supplier_code={supplier_code} brief_id={brief_id}",
            extra={'error': six.text_type(e), 'supplier_code': current_user.supplier_code, 'brief_id': brief['id']}
        )

        abort(503, "Clarification question email failed to send")

    data_api_client.create_audit_event(
        audit_type=AuditTypes.send_clarification_question,
        user=current_user.email_address,
        object_type="briefs",
        object_id=brief['id'],
        data={"question": clarification_question, "briefId": brief['id']})

    # Send the supplier a copy of the question
    supplier_email_body = render_template(
        "emails/brief_clarification_question_confirmation.html",
        brief_id=brief['id'],
        brief_name=brief['title'],
        framework_slug=brief['frameworkSlug'],
        message=clarification_question,
        supplier_name=current_user.name,
    )
    try:
        send_email(
            to_email_addresses=[current_user.email_address],
            email_body=supplier_email_body,
            subject=u"Your question about ‘{}’".format(brief['title']),
            from_email=current_app.config['CLARIFICATION_EMAIL_FROM'],
            from_name=current_app.config['CLARIFICATION_EMAIL_NAME']
        )
    except EmailError as e:
        current_app.logger.error(
            'Brief question supplier email failed to send. error={error} supplier_code={supplier_code} brief_id={brief_id}',  # noqa
            extra={'error': six.text_type(e), 'supplier_code': current_user.supplier_code, 'brief_id': brief['id']}
        )


def get_brief_user_emails(brief):
    return [user['emailAddress'] for user in brief['users'] if user['active']]
