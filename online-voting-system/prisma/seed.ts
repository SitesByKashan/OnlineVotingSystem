import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

const adminHash =
  "smartvote_admin_seed_salt_2026$kJETY7Ot8s2Zvt7//SWXX406J4s/ZK7tbSJu/C/cwbk=";
const voterHash =
  "smartvote_voter_seed_salt_2026$Xy3YBZJtqhSOTUT1DfhDL6SakUcyvYjH5su4XhEOfmU=";

async function main() {
  const superAdmin = await prisma.user.upsert({
    where: { email: "admin@gmail.com" },
    update: {
      fullName: "Election Super Admin",
      passwordHash: adminHash,
      role: "SUPER_ADMIN",
      isEmailVerified: true,
      isBlocked: false,
    },
    create: {
      fullName: "Election Super Admin",
      email: "admin@gmail.com",
      passwordHash: adminHash,
      role: "SUPER_ADMIN",
      isEmailVerified: true,
    },
  });

  const securityAdmin = await prisma.user.upsert({
    where: { email: "security.admin@example.com" },
    update: {},
    create: {
      fullName: "Security Admin",
      email: "security.admin@example.com",
      passwordHash: adminHash,
      role: "ADMIN",
      isEmailVerified: true,
    },
  });

  const voterAyesha = await prisma.user.upsert({
    where: { email: "ayesha.voter@example.com" },
    update: {},
    create: {
      fullName: "Ayesha Demo Voter",
      email: "ayesha.voter@example.com",
      passwordHash: voterHash,
      role: "VOTER",
      isEmailVerified: true,
    },
  });

  const voterBilal = await prisma.user.upsert({
    where: { email: "bilal.voter@example.com" },
    update: {},
    create: {
      fullName: "Bilal Demo Voter",
      email: "bilal.voter@example.com",
      passwordHash: voterHash,
      role: "VOTER",
      isEmailVerified: true,
    },
  });

  const mainElection = await prisma.election.upsert({
    where: { id: 1 },
    update: {},
    create: {
      title: "SSUET Student Council Election 2026",
      description: "Main student council election for exhibition demo.",
      status: "ACTIVE",
      startTime: new Date("2026-06-13T09:00:00.000Z"),
      endTime: new Date("2026-06-13T17:00:00.000Z"),
      createdBy: superAdmin.id,
    },
  });

  await prisma.election.upsert({
    where: { id: 2 },
    update: {},
    create: {
      title: "Computer Science Society Poll",
      description: "Demo departmental poll for DSA and AI showcase.",
      status: "DRAFT",
      createdBy: superAdmin.id,
    },
  });

  const candidates = [
    {
      id: 1,
      name: "Ayesha Khan",
      party: "Future Alliance",
      manifesto: "Digital campuses, transparent student funds, and AI-supported student services.",
      color: "cyan",
    },
    {
      id: 2,
      name: "Bilal Ahmed",
      party: "Civic Reform",
      manifesto: "Fair representation, secure records, and faster complaint resolution.",
      color: "green",
    },
    {
      id: 3,
      name: "Zara Malik",
      party: "Unity Front",
      manifesto: "Inclusive events, scholarship discovery, and student wellbeing support.",
      color: "amber",
    },
  ];

  for (const candidate of candidates) {
    await prisma.candidate.upsert({
      where: { id: candidate.id },
      update: {},
      create: {
        ...candidate,
        electionId: mainElection.id,
      },
    });
  }

  await prisma.vote.upsert({
    where: { receiptCode: "SV-DEMO-A1B2C3" },
    update: {},
    create: {
      userId: voterAyesha.id,
      electionId: mainElection.id,
      candidateId: 1,
      receiptCode: "SV-DEMO-A1B2C3",
      receiptQrPayload: JSON.stringify({
        receipt: "SV-DEMO-A1B2C3",
        electionId: mainElection.id,
        verified: true,
      }),
      receiptQrPath: "/receipts/SV-DEMO-A1B2C3.png",
      ipAddress: "127.0.0.1",
      deviceHash: "demo-device-ayesha",
    },
  });

  const auditLogs = [
    {
      id: 1,
        actorId: superAdmin.id,
        actorEmail: superAdmin.email,
        module: "ADMIN",
        action: "ELECTION_CREATED",
        detail: "Seed election created for demo.",
        severity: "LOW",
        ipAddress: "127.0.0.1",
        metadataJson: JSON.stringify({ electionId: mainElection.id }),
    },
    {
      id: 2,
        actorId: voterAyesha.id,
        actorEmail: voterAyesha.email,
        module: "VOTE",
        action: "VOTE_CAST",
        detail: "Demo vote receipt SV-DEMO-A1B2C3 issued.",
        severity: "LOW",
        ipAddress: "127.0.0.1",
        metadataJson: JSON.stringify({ receipt: "SV-DEMO-A1B2C3" }),
    },
    {
      id: 3,
        actorId: securityAdmin.id,
        actorEmail: securityAdmin.email,
        module: "SECURITY",
        action: "ADMIN_SECURITY_REVIEW",
        detail: "Seed security admin reviewed the election.",
        severity: "LOW",
    },
  ];
  for (const log of auditLogs) {
    await prisma.auditLog.upsert({
      where: { id: log.id },
      update: {},
      create: log,
    });
  }

  const securityEvents = [
    {
      id: 1,
        userId: voterAyesha.id,
        eventType: "NORMAL_VOTE",
        riskScore: 5,
        ipAddress: "127.0.0.1",
        deviceHash: "demo-device-ayesha",
        description: "Verified voter cast one valid vote.",
        metadataJson: JSON.stringify({ electionId: mainElection.id }),
    },
    {
      id: 2,
        userId: voterBilal.id,
        eventType: "FAILED_LOGIN",
        riskScore: 35,
        ipAddress: "127.0.0.1",
        deviceHash: "demo-device-bilal",
        description: "Failed login attempt captured for monitoring.",
        metadataJson: JSON.stringify({ attempts: 1 }),
    },
  ];
  for (const event of securityEvents) {
    await prisma.securityEvent.upsert({
      where: { id: event.id },
      update: {},
      create: event,
    });
  }

  const aiAlerts = [
    {
      id: 1,
        electionId: mainElection.id,
        alertType: "SECURITY",
        severity: 1,
        title: "System Healthy",
        message: "No critical security alerts detected.",
        status: "OPEN",
        metadataJson: JSON.stringify({ source: "seed" }),
    },
    {
      id: 2,
        electionId: mainElection.id,
        alertType: "TURNOUT",
        severity: 2,
        title: "Turnout Watch",
        message: "Monitor vote count during live demo.",
        status: "OPEN",
        metadataJson: JSON.stringify({ threshold: 80 }),
    },
  ];
  for (const alert of aiAlerts) {
    await prisma.aiAlert.upsert({
      where: { id: alert.id },
      update: {},
      create: alert,
    });
  }

  const notifications = [
    {
      id: 1,
        userId: superAdmin.id,
        roleTarget: "SUPER_ADMIN",
        title: "Election Started",
        message: "SSUET Student Council Election is active.",
        type: "SUCCESS",
    },
    {
      id: 2,
        roleTarget: "ADMIN",
        title: "AI Agent Ready",
        message: "AI fraud detection and live monitoring are enabled.",
        type: "INFO",
    },
  ];
  for (const notification of notifications) {
    await prisma.notification.upsert({
      where: { id: notification.id },
      update: {},
      create: notification,
    });
  }

  const dsaOperations = [
    {
      id: 1,
        module: "QUEUE",
        operation: "ENQUEUE_OTP_EMAIL",
        inputJson: JSON.stringify({ email: voterAyesha.email }),
        outputJson: JSON.stringify({ position: 1 }),
        explanation: "OTP email jobs are processed in FIFO order.",
    },
    {
      id: 2,
        module: "STACK",
        operation: "PUSH_ADMIN_ACTION",
        inputJson: JSON.stringify({ action: "ELECTION_CREATED" }),
        outputJson: JSON.stringify({ stackSize: 1 }),
        explanation: "Admin actions can be tracked using stack behavior.",
    },
    {
      id: 3,
        module: "HASH_TABLE",
        operation: "LOOKUP_VOTER_STATUS",
        inputJson: JSON.stringify({ email: voterAyesha.email }),
        outputJson: JSON.stringify({ hasVoted: true }),
        explanation: "Hash table lookup gives fast voter status checks.",
    },
    {
      id: 4,
        module: "BINARY_SEARCH",
        operation: "SEARCH_AUDIT_BY_TIME",
        inputJson: JSON.stringify({ timestamp: "2026-06-13T09:00:00.000Z" }),
        outputJson: JSON.stringify({ found: true }),
        explanation: "Sorted audit logs can be searched using binary search.",
    },
    {
      id: 5,
        module: "GRAPH",
        operation: "ADD_DEVICE_EDGE",
        inputJson: JSON.stringify({ user: "ayesha", device: "demo-device-ayesha" }),
        outputJson: JSON.stringify({ edges: 1 }),
        explanation: "User-device-IP relationships can be modeled as a graph.",
    },
    {
      id: 6,
        module: "PRIORITY_QUEUE",
        operation: "PUSH_AI_ALERT",
        inputJson: JSON.stringify({ severity: 2 }),
        outputJson: JSON.stringify({ topSeverity: 2 }),
        explanation: "AI alerts are prioritized by risk severity.",
    },
  ];
  for (const operation of dsaOperations) {
    await prisma.dsaOperation.upsert({
      where: { id: operation.id },
      update: {},
      create: operation,
    });
  }
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (error) => {
    console.error(error);
    await prisma.$disconnect();
    process.exit(1);
  });
