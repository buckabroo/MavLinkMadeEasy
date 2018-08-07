from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse

from .forms import *

from datetime import datetime

'''
@getUserByEmail searches the User table to find the User object with a corresponding email
@param e: the email being searched for
'''
def getUserByEmail(e):
    userTable = User.objects.all()
    for cu in userTable:
        if cu.email == e:
            return cu

'''
@getDegree searches the Degree table to find the Degree object with corresponding degree and major
@param d: degree attribute of Degree being searched for
@param m: major attribute of Degree being searched for
'''
def getDegree(d, m):
    degreeTable = Degree.objects.all()
    for deg in degreeTable:
        if deg.major == m and deg.degree == d:
            return deg

'''
@getCompletedByUser provides a list of Course (objects) the user has taken
@param uID: the primary key corresponding to the active user
'''
def getCompletedByUser(uID):
    cu = User.objects.get(pk=uID)
    print("Current user: %s" % cu)
    completedCourses = []
    for cc in Complete.objects.get(user=cu).complete.all():
        completedCourses.append(cc)
    return completedCourses

'''
@getCoursesForUser provides a list of Course (objects) the user must complete for their respective Degree
@param uID: the primary key corresponding to the active user
'''
def getCoursesForUser(uID):
    requiredCourses = []
    reqs = Degree.objects.get(user=uID).req.all()
    for r in reqs:
        catalog = r.course.all()
        for g in catalog:
            requiredCourses.append(g)
            prereqs = Course.objects.get(id=g.id).prereqs.all()
            for pr in prereqs:
                additionalCourse = Course.objects.get(id=pr.prereq.id)
                if additionalCourse not in requiredCourses:
                    requiredCourses.append(additionalCourse)
    print( "Number of required Courses:")
    print( len(requiredCourses) )
    return requiredCourses

'''
@removeCoursesTaken provides a list of Course (objects) the user must still take (required, but not completed classes)
@param requiredClasses: a list of Course (objects) required for the User's Degree
@param classesTaken: a list of Course (objects) that the User has already completed
'''
def removeCoursesTaken( requiredClasses, classesTaken ):
    validCourses = []
    for rc in requiredClasses:
        if rc not in classesTaken :
            validCourses.append(rc)
    return validCourses

'''
@checkPrereqsMet determines if the User has met all Prereqs for a particular Course
@param prereqs: a list of Course (objects) corresponding to Prereqs for a given Course
@param classesTaken: a list of Course (objects) that the User has already completed
@parm scheduledClasses: a list of Course (objects) the scheduling algorithm has accounted for already
'''
def checkPrereqsMet(preqreqs, classesTaken):
    met = True
    for pr in preqreqs:
        if pr.prereq not in classesTaken and pr.this_or not in classesTaken:
            met = False
            break
    return met

'''
@checkOfferedSemester determines if a given Course if offered during the current semester
@param course: the Course under test
@param ssf: the Spring, Summer, Fall, offering attribute of the Course
'''
def checkOfferedSemester(course, ssf):
    offered = False
    if course.semester == ssf or course.semester == 'All':
        offered = True
    return offered

'''
@checkCourseValid determines if a given Course can be taken during a given semester
@param course: the Course under test
@param classesTaken: a list of Course (objects) that the User has already completed
@parm scheduledClasses: a list of Course (objects) the scheduling algorithm has accounted for already
@param ssf: the Spring, Summer, Fall, offering attribute of the Course
'''
def checkCourseValid(course, classesTaken, ssf): #checkCourseValid( nc, classesTaken, semesterCourses, ssfSemester )
    valid = False
    prereqs = course.prereqs.all()
    prereqsMet = checkPrereqsMet(prereqs, classesTaken)
    offered = checkOfferedSemester(course, ssf)
    if prereqsMet and offered:
        valid = True
    return valid

'''
@getSemesterByMonthYear determines semester (Spring, Summer, Fall) according to current month
@param m: current month
'''
def getSemesterByMonthYear( m ):
    if  m < 5 :
        title = "Spring"
    elif  m < 8 :
        title = "Summer"
    else:
        title = "Fall"
    return title

'''
@generateNewSemester creates a new logical semester
@param semester: previous semester list
'''
def generateNewSemester(semester):
    ssf = semester[0]
    nextSemester = ""
    y = semester[1]
    if ssf == "Spring" :
        nextSemester = "Summer"
    elif ssf == "Summer" :
        nextSemester = "Fall"
    else:
        nextSemester ="Spring"
        y += 1
    semester[0] = nextSemester
    semester[1] = y
    semester[2] = []
    return semester

'''
@isFull determines if a semester has hit the maximum number of credits allowable
@param courseList: list of Course (objects) the user is scheduled to take during current semester
'''
def isFull(courseList):
    full = False
    totalCredits = 0
    for c in courseList:
        totalCredits+= c.credits
    if totalCredits >= 12 and totalCredits <= 16:
        full = True
    return full

'''
@createSchedule generates semester-by-semester schedule for User's needed Courses according to Degree
@param uID: primary key associated with active user
'''
def createSchedule(uID):
    loopCount = 0
    reqTracker = [] #used to track if Req credit quotas have been met
    requiredClasses = getCoursesForUser(uID)
    reqs = Degree.objects.get(user=uID).req.all()
    for r in reqs:
        req_id = r.id
        req_name = r.name
        req_type = r.req_type
        req_creds = r.credits
        req_start = 0
        reqTracker.append([req_id, req_name, req_type, req_creds, req_start])
    print( "Required classes length: %s" % len(requiredClasses))
    classesTaken = getCompletedByUser(uID)
    print("Classes taken length: %s" % len(classesTaken))
    neededClasses = removeCoursesTaken( requiredClasses, classesTaken )
    print("Needed classes length: %s" % len(neededClasses))
    schedule = []
    currentMonth = datetime.now().month
    currentYear = datetime.now().year
    ssfSemester = getSemesterByMonthYear(currentMonth)
    semester = [ssfSemester, currentYear, []]
    currentSemester = generateNewSemester(semester)
    total = 0
    while neededClasses != [] and loopCount < 30:
        loopCount+=1
        print( loopCount )
        print( "neededClasses now: %s" % len(neededClasses) )
        for nc in neededClasses:
            print( nc )
            if ( checkCourseValid( nc, classesTaken, ssfSemester ) ):
                print( "Course valid!" )
                currentSemester[2].append(nc)
                classesTaken.append(nc)
                neededClasses.remove(nc)
                for r in reqTracker: # determine which Req this course falls under
                    if nc in Req.objects.get(id=r[0]).course.all():
                        r[4]+=nc.credits # increment the completed running total for that Req
                        if r[3] <= r[4]: # determine if the max number of credits has been reached for that Req
                            for c in neededClasses: # eliminate all the other courses in the Req from needed classes
                                if c in Req.objects.get(id=r[0]).course.all():
                                    neededClasses.remove(c)
            if ( neededClasses != [] and isFull(semester[2])):
                schedule.append(semester[:])
                total += len(semester[2])
                semester = generateNewSemester(semester)
                print( "Starting new semester!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                break
    schedule.append(semester[:])
    print("Schedule classes length:")
    print(total)
    return schedule

'''
@generateCheckBoxEntities creates a list of tuples of requirements, course names and numbers for the selectcourses page
@param uID: primary key corresponding to the active user
'''
def generateCheckBoxEntities(uID):
    reqs = Degree.objects.get(user=uID).req.all()
    total = 0
    checkBoxEntities = []
    for r in reqs:
        req_id = r.id
        req_name = r.name
        req_type = r.req_type
        req_creds = r.credits
        catalog = r.course.all()
        courseList = []
        for g in catalog:
            number = g.num
            name = g.name
            creds = g.credits
            courseList.append([number,name,creds])
            total+= 1
        checkBoxEntities.append([req_id, req_name, req_type, req_creds, courseList])
    print( "Checkboxes: %s" % total)
    return checkBoxEntities

'''
@generateMajorDD creates a list of possible majors for use on the createuser page
'''
def generateMajorDD():
    allDegrees = Degree.objects.all()
    majors = []
    for d in allDegrees:
        if d.major not in majors:
            majors.append(d.major)
    return majors

'''
@emailFound provides feedback if the email is already in the User database table
@param email: email under test
'''
def emailFound(email):
    found = False
    userTable = User.objects.all()
    for cu in userTable:
        if cu.email == email:
            found = True
    return found

'''
@saveClassesToUser updates database with a list of the user has taken
@param classesChecked: list of courses the user specified as having taken
@param uID: pk of the associated active user
'''
def saveClassesToUser(classesChecked, uID):
    u = User.objects.get(pk=uID)
    if u in Complete.objects.all():
        print("Found a user with same ID, so setting complete to it!")
        completed = Complete.objects.get(user_id=u)
    else:
        print("Creating new user!")
        completed = Complete(user=u)
        completed.save()
    for cc in classesChecked:
        c = Course.objects.get(num=cc)
        print( c )
        completed.complete.add(c)
        completed.save()

'''
@removeUserCompletedEntries updates database to remove courses completed from a particular user
@param uID: pk of the associated active user
'''
def removeUserCompletedEnteries(uID):
    u = User.objects.get(pk=uID)
    completedTable = Complete.objects.all()
    for ce in completedTable:
        if ce.user == u:
            ce.delete()


########################################################################################################################
########################################################################################################################

'''
@login send a request to render the login.html page
@param request: generates the response
'''
def login(request):
    if request.method == "POST":
        emailForm = EmailForm(request.POST, prefix = "e")
        if emailForm.is_valid():
            eF = emailForm.save(commit=False)
            if emailFound(eF.email):
                u = getUserByEmail(eF.email)
                userID = u.id
                return HttpResponseRedirect(reverse('landing:schedule', args=(userID,)))
            else:
                emailForm = EmailForm(prefix="e")
                message = "Email not found"
                return render(request, 'landing/login.html', {'emailForm': emailForm, 'message':message})
    else:
        emailForm = EmailForm(prefix="e")
    return render(request, 'landing/login.html', {'emailForm': emailForm, })

'''
@selectcourses send a request to render the selectcourses.html page
@param request: generates the response
@param pk: primary key corresponding to active user
'''
def selectcourses(request, pk):
    if request.method == "POST":
        removeUserCompletedEnteries(pk)
        classesChecked = request.POST.getlist('chexmix')
        print( classesChecked )
        saveClassesToUser(classesChecked, pk)
        return HttpResponseRedirect(reverse('landing:schedule', args=(pk,)))
    else:
        checkBoxes = generateCheckBoxEntities(pk)
        # might need to write some logic here to determine if boxes have already been checked :)
    return render(request, 'landing/selectcourses.html', {'checkBoxes': generateCheckBoxEntities(pk)})

'''
@schedule send a request to render the schedule.html page
@param request: generates the response
@param pk: primary key corresponding to active user
'''
def schedule(request, pk):
    return render(request, 'landing/schedule.html', {'schedule': createSchedule(pk), 'userID': pk})

'''
@createuser send a request to render the createuser.html page
@param request: generates the response
'''
def createuser(request):
    if request.method == "POST":
        emailForm = EmailForm(request.POST, prefix = "e")
        degreeForm = DegreeForm( request.POST, prefix = "d")
        if emailForm.is_valid() and degreeForm.is_valid():
            dF = degreeForm.save(commit=False)
            eF = emailForm.save(commit=False)
            selectedMajor = request.POST['d-major']
            deg = getDegree(dF.degree, selectedMajor)
            if emailFound(eF.email):
                message = "Email already active"
                emailForm = EmailForm(prefix="e")
                degreeForm = DegreeForm(prefix="d")
                majors = generateMajorDD()
                return render(request, 'landing/createuser.html', {'emailForm': emailForm, 'degreeForm':degreeForm, 'message': message, 'majors':majors})
            else:
                u = User(email = eF.email, degree=deg)
                u.save()
                userID = u.id
                return HttpResponseRedirect(reverse('landing:selectcourses', args=(userID,)))
    else:
        emailForm = EmailForm(prefix="e")
        degreeForm = DegreeForm(prefix="d")
        majors = generateMajorDD()
    return render(request, 'landing/createuser.html', {'emailForm': emailForm, 'degreeForm':degreeForm, 'majors':generateMajorDD()})
