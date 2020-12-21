import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SINGLE_LINE_LENGTH = 80
DOUBLE_LINE_LENGTH = 47
FOOTER_TEXT = os.environ['AdditionalEmailFooterText']
HEADER_TEXT = 'Weekly Security Hub Report \n'
FOOTER_URL = 'https://console.aws.amazon.com/securityhub/home/standards#/standards'

# this function will add a horizontal line to the email
def add_horizontal_line(text_body, line_char, line_length):
    y = 0
    while y <= line_length:
        text_body += line_char
        y += 1
    text_body += '\n'
    
    return text_body

def lambda_handler(event, context):
    
    insightArns = []
    insightLabels = []
    #this is the placement number of insights that are grouped by severity, this is used for reversing the sort
    severityTypeInsights = [1,2,3,4] 
    
    #fetch arns for custom insights from lambda environment variables 
    insightArns.append(os.environ['ARNInsight01'])
    insightArns.append(os.environ['ARNInsight02'])
    insightArns.append(os.environ['ARNInsight03'])
    insightArns.append(os.environ['ARNInsight04'])
    insightArns.append(os.environ['ARNInsight05'])
    insightArns.append(os.environ['ARNInsight06'])
    insightArns.append(os.environ['ARNInsight07'])
    
    #fetch the SNS arn to send the email body to, from lambda environment variables
    snsTopicArn = os.environ['SNSTopic']

    #determine region from the arns
    arnParsed = insightArns[0].split(':')
    region = arnParsed[3]

    #create list of section labels 
    insightLabels.append('AWS Foundational Security Best Practices security checks:')
    insightLabels.append('AWS Foundational Security Best Practices failed security checks by severity:')
    insightLabels.append('GuardDuty threat detection findings by severity:')
    insightLabels.append('IAM Access Analyzer findings by severity:')
    insightLabels.append('Unresolved findings by severity:')
    insightLabels.append('New findings in the last 7 days:')
    insightLabels.append('Top 10 Resource Types with findings:')
    
    #format Email header
    snsBody = ''
    snsBody = add_horizontal_line(snsBody, '=', DOUBLE_LINE_LENGTH)
    snsBody += HEADER_TEXT
    snsBody = add_horizontal_line(snsBody, '=', DOUBLE_LINE_LENGTH)
    snsBody += '\n\n'
    
    #create boto3 client for Security Hub API calls
    sec_hub_client = boto3.client('securityhub')
    
    #for each custom insight get results and format for email
    i = 0
    while i < len(insightArns):
        
        #call security hub api to get results for each custom insight
        response = sec_hub_client.get_insight_results(
            InsightArn=insightArns[i]
        )
        insightResults = response['InsightResults']['ResultValues']
        
        #format into an email - section header
        snsBody += str(insightLabels[i]) + '\n'
        snsBody = add_horizontal_line(snsBody,'-', SINGLE_LINE_LENGTH)

        #check for blank custom insights
        if len(insightResults) == 0:
            snsBody += 'NO RESULTS \n'
        
        #determine how many rows are in this section, cap at 10
        totalRows = len(insightResults)
        if totalRows > 10:
            totalRows = 10
        
        #determine if this is the first section to customize the label
        if i == 0:
            firstSection = True
        else:
            firstSection = False
        
        #determine if this is an insight that needs an updated sort
        if (i in severityTypeInsights): 
            #reverse the sort
            insightResults.reverse()

        #convert the API results into rows for email formatting    
        x = 0   
        while x < totalRows:
            
            snsBody  +=  str(insightResults[x]['Count']) #add the value
            snsBody += '\t - \t'    #add a divider
            if firstSection: #add two extra labels (TOTAL and CHECKS) to the values for the foundational summary 
                snsBody += 'TOTAL '
                snsBody += str(insightResults[x]['GroupByAttributeValue']) #add the label
                snsBody += ' CHECKS'
            else:
                snsBody += str(insightResults[x]['GroupByAttributeValue']) #add the label
                
            snsBody += '\n' #next line
            x += 1
        
        #add table footer
        snsBody = add_horizontal_line(snsBody,'-', SINGLE_LINE_LENGTH)
        snsBody +=' \n'

        #create and add deep link for this section
        insightLink = 'https://' + region + '.console.aws.amazon.com/securityhub/home?region='
        insightLink += region + '#/insights/' + insightArns[i]
        snsBody += insightLink

        snsBody += ' \n\n'
        i += 1
    
    #add footer text  
    snsBody += FOOTER_TEXT
    snsBody += '\n'
    snsBody = add_horizontal_line(snsBody,'-', SINGLE_LINE_LENGTH)
    snsBody += FOOTER_URL

    #send to SNS
    sns_client = boto3.client('sns')

    response = sns_client.publish(
        TopicArn=snsTopicArn,
        Message=snsBody
    )

    return {
        'statusCode': 200,
    }
