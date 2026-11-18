typedef Json = Map<String, dynamic>;

class Member {
  Member.fromJson(Json json)
    : handle = json['handle'] as String,
      displayName = json['display_name'] as String,
      isOrganizer = json['role'] == 'organizer';

  final String handle;
  final String displayName;
  final bool isOrganizer;
}

class Activity {
  Activity.fromJson(Json json)
    : id = json['id'] as String,
      title = json['title'] as String,
      description = json['description'] as String,
      location = json['location'] as String,
      organizer = json['organizer'] as String,
      startsAt = DateTime.parse(json['starts_at'] as String).toLocal(),
      endsAt = DateTime.parse(json['ends_at'] as String).toLocal(),
      reward = json['reward'] as int,
      inProgress = json['in_progress'] as bool,
      attended = json['attended'] as bool,
      canIssueCode = json['can_issue_code'] as bool;

  final String id;
  final String title;
  final String description;
  final String location;
  final String organizer;
  final DateTime startsAt;
  final DateTime endsAt;
  final int reward;
  final bool inProgress;
  final bool attended;
  final bool canIssueCode;
}

class CheckinCode {
  CheckinCode.fromJson(Json json)
    : code = json['code'] as String,
      expiresAt = DateTime.parse(json['expires_at'] as String).toLocal();

  final String code;
  final DateTime expiresAt;
}

class Attendance {
  Attendance.fromJson(Json json)
    : points = json['points'] as int,
      alreadyRecorded = json['already_recorded'] as bool;

  final int points;
  final bool alreadyRecorded;
}

class Wallet {
  Wallet.fromJson(Json json)
    : balance = json['balance'] as int,
      movements = (json['movements'] as List)
          .cast<Json>()
          .map(Movement.fromJson)
          .toList();

  final int balance;
  final List<Movement> movements;
}

class Movement {
  Movement.fromJson(Json json)
    : isAttendance = json['kind'] == 'attendance',
      points = json['points'] as int,
      label = json['label'] as String,
      createdAt = DateTime.parse(json['created_at'] as String).toLocal();

  final bool isAttendance;
  final int points;
  final String label;
  final DateTime createdAt;
}

class RankEntry {
  RankEntry.fromJson(Json json)
    : handle = json['handle'] as String,
      displayName = json['display_name'] as String,
      position = json['position'] as int,
      points = json['points'] as int;

  final String handle;
  final String displayName;
  final int position;
  final int points;
}
