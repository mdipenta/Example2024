#! /usr/bin/python3

import os
import re
import datetime
import json
import sys
import subprocess
import pydriller

def getGit(directory):
    return pydriller.Git(directory)

def runCmdList(commands):
    try:
        x = subprocess.check_output(commands)
        lines=str(x.decode("latin-1",errors='ignore')).splitlines()
        return lines
    except:
        return []


def runCmd(command):
    try:
        x = subprocess.check_output(re.split(" ",command))
        lines=str(x.decode("latin-1",errors='ignore')).splitlines()
        return lines
    except:
        return []

def isSourceCode(fileName,lang):
    languages={"java":"java","python":"py","csharp":"cs","unity":"cs|asset|anim|prefab"}
    testString="/test/|/testcases|/tests/"
    excludeTests=True
    if re.search("\.("+languages[lang]+")$",fileName):
        if excludeTests and (re.search(testString,fileName,re.IGNORECASE)):
            return False
        else:
            return True
    return False

def gitNoRepo(repo):
    return "git -C "+repo

def getChangedFiles(repo,commit):
    changedFiles=[]
    c=repo.get_commit(commit)
    for f in(c.modified_files):
        if f.old_path and f.new_path:
            rec={}
            rec["old"]=f.old_path
            rec["new"]=f.new_path
            changedFiles.append(rec)
    return changedFiles

# def getChangedFiles(repoDir,commitId):
#     gitNoRepo(repoDir)
#     command=gitNoRepo(repoDir)+" diff --name-status "+commitId+"^ "+commitId
#     #print(command)
#     changedFiles=[]
#     with os.popen(command) as f:
#         chfiles=f.readlines()
#         for file in chfiles:
#             file=file.rstrip("\n")
#             match=re.search("(\w)\s+",file)
#             filename=match.string[match.end():]
#             changeType=match.group(1)
#             if changeType=="M" or changeType=="R":
#                 changedFiles.append(filename)
#         return changedFiles

def getFilesLang(files,lang):
    lfiles=[]
    for f in files:
        #f=f.rstrip("\n")
        if(isSourceCode(f['new'],lang)):
            lfiles.append(f)
    return lfiles




#Approximated and faster comment matching
def isComment(stringLine):
    if re.search("^\\s*$", stringLine) or re.search("^\\s*//", stringLine) or (re.search("^\\s*/\\*", stringLine) and ((not re.search("\\*/", stringLine)) or re.search("\\*/\\s*$", stringLine))) \
            or (not re.search("^\\s*/\\*", stringLine) and re.search("\\*/\\s*$", stringLine)) or re.search("^\\s*\\*",stringLine):
                    return True
    return False


def isCommentPy(stringLine):
    if re.search("^\\s*$", stringLine) or re.search("^\\s*#", stringLine):
        return True
    return False


#Better comment matching
def getCommentLines(fileLines,extension):
    lang=extension.lower()
    if lang=="java" or lang=="c" or lang=="cpp" or lang=="h" or lang=="cs":
        return getCommentLinesJava(fileLines)
    if lang=="py":
        return getCommentLinesPython(fileLines)
    if lang=="cs":
        return getCommentLinesJava(fileLines)
    else:
        return getCommentLinesNone(fileLines)



def getCommentLinesNone(fileLines):
    comments=[]
    for stringLine in fileLines:
        comments.append(False)
    return comments

def getCommentLinesJava(fileLines):
    inComment=False
    n=0
    comments=[]
    for stringLine in fileLines:
        n=n+1
        thisLineComment=False
        #Find a closing comment not at the end of the line
        if re.search("\\*/\s*\S+",stringLine):
            inComment=False
        if re.search("^\\s*$",stringLine) or re.search("^\\s*//", stringLine) or (re.search("^\\s*/\\*", stringLine) and
                ((not re.search("\\*/", stringLine)) or re.search("\\*/\\s*$", stringLine))) or\
                (not re.search("\\*", stringLine) and re.search("\\*/\\s*$", stringLine)) or inComment:
            thisLineComment=True
        #Find an opening comment never closed
        if re.search("\\*/",stringLine):
            inComment=False
        if re.search("/\\*",stringLine) and not re.search("\\*/",stringLine):
            inComment=True
        comments.append(thisLineComment)
    return comments



def getCommentLinesPython(fileLines):
    inComment=False
    n=0
    comments=[]
    for stringLine in fileLines:
        n=n+1
        thisLineComment=False
        #Find an opening comment
        if re.search(r"^\s*\"\"\"",stringLine):
            inComment=True
        if re.search("^\\s*$",stringLine) or re.search(r"^\s*#",stringLine)  or inComment:
            thisLineComment=True
        comments.append(thisLineComment)
        if re.search(r"\"\"\"\s+$",stringLine):
            inComment=False
    return comments






def getChangedLines(repoDir,commit,fileOld,fileNew,lang):
    #fCommand=gitNoRepo(repoDir)+" show "
    #fileLines=[]
    fileLines=runCmdList(["git","-C",repoDir,"show",commit+"^:"+fileOld])
    match=re.search(r"\.(\w+)$",fileOld)
    fileExtension=match.group(1)
    comments=getCommentLines(fileLines,fileExtension)

    #fileLines=f.readlines()

    commandList=["git","-C",repoDir,"diff","--histogram","--unified=0","-w",commit+"^:"+fileOld,commit+":"+fileNew]
    chLines=[]
    changedlines=runCmdList(commandList)
        #chlines=f.readlines()
    for l in changedlines:
        if re.search("^@@",l):
            lineItems=re.split("@@",l)
            TotalChangedLines=0
            lineStart=0
            match=re.search("-(\d+),(\d+)",lineItems[1])
            if match:
                lineStart=eval(match.group(1))
                TotalChangedLines=eval(match.group(2))
            else:
                match=re.search("-(\d+)",lineItems[1])
                if match:
                    lineStart=eval(match.group(1))
                    TotalChangedLines=1

            if TotalChangedLines>0:
                for lineNo in range(lineStart,lineStart+TotalChangedLines):
                    if not comments[lineNo-1]:
                        chLines.append(lineNo)
    #print("File: "+file+" changed lines "+str(chLines))
    return chLines


def getChangedLinesMap(repoDir,commit,fileOld,fileNew):
    commandList=["git","-C",repoDir,"diff","--histogram","--unified=0",commit+"^:"+fileOld,commit+":"+fileNew]
    chLines=[]
    changedlines=runCmdList(commandList)

    for l in changedlines:
        if re.search("^@@",l):
            lineItems=re.split("@@",l)
            TotalChangedLinesLeft=0
            TotalChangedLinesRight=0
            lineStartLeft=0
            lineStartRight=0
            match=re.search("-(\d+),(\d+)",lineItems[1])
            if match:
                lineStartLeft=eval(match.group(1))
                TotalChangedLinesLeft=eval(match.group(2))
            else:
                match=re.search("-(\d+)",lineItems[1])
                if match:
                    lineStartLeft=eval(match.group(1))
                    TotalChangedLinesLeft=1

            match=re.search(r"\+(\d+),(\d+)",lineItems[1])
            if match:
                lineStartRight=eval(match.group(1))
                TotalChangedLinesRight=eval(match.group(2))
            else:
                match=re.search(r"\+(\d+)",lineItems[1])
                if match:
                    lineStartRight=eval(match.group(1))
                    TotalChangedLinesRight=1

            LeftStart=0
            LeftEnd=0
            if TotalChangedLinesLeft>0:
                LeftStart=lineStartLeft
                LeftEnd=LeftStart+TotalChangedLinesLeft-1

            RightStart=0
            RightEnd=0
            if TotalChangedLinesRight>0:
                RightStart=lineStartRight
                RightEnd=RightStart+TotalChangedLinesRight-1

            chLines.append((LeftStart,LeftEnd,RightStart,RightEnd))

    return chLines


def blameLine(repoDir,commitId,file,line,newFileName):
    command=gitNoRepo(repoDir)+" blame -w -p -L "+str(line)+","+str(line) +" -c "+commitId+"^ "+file
    blameCommit=""
    origin=""
    commitTime=0
    blameRes=runCmd(command)
    committerTz = "+0000"
    if len(blameRes)>0 and not re.search("^fatal:",blameRes[1]):
        mapping=blameRes[0]
        ts=blameRes[3]
        tz = blameRes[4]
        match=re.search("(\\w+) (\\d+) (\\d+)",mapping)
        if match:
            blameCommit=match.group(1)
            origin=match.group(2)
        matchTime=re.search("(\\d+)$",ts)
        if matchTime:
            commitTime=eval(matchTime.group(1))
        matchTz=re.search("^author-tz ([+-]\\d+)",tz)
        if matchTz:
            committerTz=matchTz.group(1)
        if newFileName=="":
            for i in range(4,len(blameRes)):
                match=re.search("^filename\\s+",blameRes[i])
                if match:
                    newFileName=match.string[match.end():]

    commitDate=datetime.datetime.fromtimestamp(commitTime)

    dateFormat = "%Y-%m-%d %H:%M:%S"
    myDate=commitDate.strftime(dateFormat)
    commitDate=datetime.datetime.strptime(myDate+" "+committerTz,dateFormat+" %z")
    return blameCommit,origin,commitDate,newFileName


def blameFile(repoDir,commit,fileName):
    #command = gitNoRepo(repoDir) + " blame -w -p -c " + commit + "^ " + fileName
    commandList=["git","-C",repoDir,"blame","-w","-p","-c",commit+"^",fileName]

    lines = runCmdList(commandList)
    nl = len(lines)
    newFileName = ""
    BlamedLines={}
    HashCommit={}
    for x in range(0, nl):
        lineObject={}
        l = lines[x]
        match = re.search("^([abcdef\\d]+)\\s+(\\d+)\\s+(\\d+)", l)
        if match:
            commitId = match.group(1)
            newLine = match.group(2)
            mapping = match.group(3)
            if not re.search("^author\\s+", lines[x + 1]):
                commitObject=HashCommit[commitId]
                lineObject['commitId']=commitId
                lineObject['newLine']=newLine
                lineObject['commitDate']=commitObject['commitDate']
                lineObject['newFileName']=commitObject['newFileName']
                BlamedLines[mapping]=lineObject
                #print("Line ", mapping, "Commit", commitId, "From Line ", newLine, "Time ", commitDate, "NewName ",
                #      newFileName)
        else:
            match = re.search("^author-time\\s+(\\d+)", l)
            if match:
                auTime = eval(match.group(1))
            else:
                match = re.search("^author-tz\\s+([-+]\\d+)", l)
                if match:
                    tZone = match.group(1)
                    commitDate = datetime.datetime.fromtimestamp(auTime)

                    dateFormat = "%Y-%m-%d %H:%M:%S"
                    myDate = commitDate.strftime(dateFormat)
                    commitDate = datetime.datetime.strptime(myDate + " " + tZone, dateFormat + " %z")
                else:
                    match = re.search("^filename\\s+", l)
                    if match:
                        if match:
                            newFileName = match.string[match.end():]
                            #print("Line ", mapping, "Commit", commitId, "From Line ", newLine, "Time ", commitDate,
                            #      "NewName ", newFileName)
                            commitObject={}
                            commitObject['commitDate']=commitDate
                            commitObject['newFileName']=newFileName
                            HashCommit[commitId]=commitObject
                            lineObject['commitId'] = commitId
                            lineObject['newLine'] = newLine
                            lineObject['commitDate'] = commitDate
                            lineObject['newFileName'] = newFileName
                            BlamedLines[mapping] = lineObject
    return BlamedLines


def identifyIntroCommits(drillerrepo,repo,commitHash,issueCreationDate,lang):
    #print(repoDir)
    #print("I'm here")
    dateFormat = '%Y-%m-%d %H:%M:%S %z'
    files=getChangedFiles(drillerrepo,commitHash)
    #print(files)
    changedLang=getFilesLang(files,lang)
    items=[]
    #print(changedLang)
    for chj in changedLang:
        item = {}
        item['filepath']=chj['new']
        item['mappings']={}
        item['filenames']={}
        item['introdates']={}
        lines=getChangedLines(repo,commitHash,chj['old'],chj['new'],lang)
        #print("Filename",chj['old'],chj['new'])
        blames=blameFile(repo,commitHash,chj['old'])
        newFileName=""
        for line in lines:
            if str(line) in blames:
                blamedLine=blames[str(line)]
                blamedCommit=blamedLine['commitId']
                mapping=blamedLine['newLine']
                introDate=blamedLine['commitDate']
                newFileName=blamedLine['newFileName']
            else:
                blamedCommit=""
            #(blamedCommit,mapping,introDate,newFileName)=blameLine(repo,commitHash,chj,line,newFileName)
            if(blamedCommit!="" and introDate<issueCreationDate):
                #print(blamedCommit,line,":",mapping,introDate)
                if not blamedCommit in item['mappings']:
                    item['mappings'][blamedCommit]={}
                item['mappings'][blamedCommit][line]=mapping
                if not blamedCommit in item['filenames']:
                    item['filenames'][blamedCommit]=newFileName
                if not blamedCommit in item['introdates']:
                    item['introdates'][blamedCommit]=introDate.strftime(dateFormat)
        if len(item['mappings'].keys())>0:
            items.append(item)
    return items

if __name__ == '__main__':

    if len(sys.argv)<4:
        print("Syntax: %s issueFile repository language" % sys.argv[0])
        exit(1)


    issueFile=sys.argv[1]
    repoDir=sys.argv[2]
    lang=sys.argv[3]


    dateFormatIssues='%Y-%m-%d %H:%M:%S %z'
    drillerrepo=pydriller.Git(repoDir)

    Annotations={}
    n=0
    with open (issueFile) as f:
        issues=json.load(f)
        numIssues=len(issues.keys())
        for(issueId,issueData) in issues.items():
            n = n + 1
            creationDate=datetime.datetime.strptime(issueData['creationdate'], dateFormatIssues)
            commitDate = datetime.datetime.strptime(issueData['commitdate'], dateFormatIssues)
            resolutionDate=datetime.datetime.strptime(issueData['resolutiondate'], dateFormatIssues)
            hash=issueData['hash']
            if(commitDate>creationDate and resolutionDate>commitDate):
                print("Analyzing issue "+issueId+" ("+str(n)+" of "+str(numIssues)+")",file=sys.stderr)
                #print(repoDir,hash,creationDate,lang)
                myItem=identifyIntroCommits(drillerrepo,repoDir,hash,creationDate,lang)
                if len(myItem)>0:
                    Annotations[hash]=myItem

    print(json.dumps(Annotations,indent=2))
