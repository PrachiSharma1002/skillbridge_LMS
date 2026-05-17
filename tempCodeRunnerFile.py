    session['user_id'] = user[0]
        session['user_name'] = user[1]
        session['role'] = user[4]
        if user[4] == 'admin':
            return redirect('/admin')
        elif user[4] == 'teacher':
            return redirect('/teacher')
        else:
            return redirect('/dashboard')